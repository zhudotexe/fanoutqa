import asyncio
import logging
import re

import mediawiki
from kani import ChatMessage, ChatRole, Kani, ToolCall, ai_function
from kani.engines.base import BaseEngine, Completion

from bench.runner import GenerationResult, Runner, argstokwargs, parser
from fanout.retrieval import Corpus
from fanout.wiki import DatedPage, wikipedia

log = logging.getLogger("openbook")


# ===== runner =====
class OpenBookRunner(Runner):
    def get_prompt(self, question, *args, **kwargs) -> str:
        question = question["question"]
        prompt = (
            "You have the ability to search Wikipedia for information. To do so, output a message in the format"
            " <search>{YOUR_SEARCH_QUERY}</search> (e.g. `<search>List of states and territories of the United"
            " States</search>`).\nAnswer the following question, and output only your answer or a search, but not"
            " both. If the answer is a list, output one on each line. Current date: 11-20-2023.\n\n[Question]:"
            f" {question}"
        )
        return prompt

    async def run_one(self, prompt, question, kani_cls=Kani, **kwargs) -> GenerationResult:
        try:
            return await asyncio.wait_for(self.run_impl(prompt, kani_cls, question=question, **kwargs), timeout=600)
        except Exception:
            log.exception("Error getting response")
            return GenerationResult(success=False, content=None, extra=None)

    async def run_impl(self, prompt, kani_cls=Kani, **kwargs):
        ai = kani_cls(self.engine, **kwargs)
        content = None
        msgs = []
        async for msg in ai.full_round(prompt):
            msgs.append(repr(msg))
            content = msg.content or content
            if msg.role == ChatRole.ASSISTANT:
                print(msg.content)
        return GenerationResult(success=True, content=content, extra=msgs)


class OpenAIOpenBookRunner(OpenBookRunner):
    def get_prompt(self, question, *args, **kwargs) -> str:
        question = question["question"]
        if self.model_name.startswith("gpt-3.5-turbo"):
            prompt = (
                "Answer the following question, and output only your answer. You may search before outputting your"
                " answer. If the answer is a list, output one on each line. Current date: 11-20-2023.\n\n[Question]:"
                f" {question}"
            )
        else:
            prompt = (
                "Answer the following question, and output only a function call or your answer. If the answer is a"
                f" list, output one on each line. Current date: 11-20-2023.\n\n[Question]: {question}"
            )
        return prompt


# ==== kani ====
class SearchEngine(BaseEngine):
    def __init__(self, engine: BaseEngine, strict=False):
        self.engine = engine
        self.strict = strict
        self.max_context_size = engine.max_context_size
        self.token_reserve = engine.token_reserve

    def message_len(self, message):
        if message.role == ChatRole.FUNCTION:
            message = message.copy_with(role=ChatRole.USER)
        return self.engine.message_len(message)

    async def predict(self, messages, functions=None, **kwargs):
        translated_messages = []
        for m in messages:
            if m.role == ChatRole.FUNCTION:
                translated_messages.append(m.copy_with(role=ChatRole.USER))
            else:
                translated_messages.append(m)
        resp = await self.engine.predict(translated_messages, functions, **kwargs)
        # search for a <search></search> pair
        content = resp.message.text
        tool_calls = None
        if self.strict:
            match = re.match(r"<search>(.+?)</search>", content)
        else:
            match = re.search(r"<search>(.+?)</search>", content)
        if match:
            content = content[: match.end()]
            tool_calls = [ToolCall.from_function("search", query=match[1])]
        return Completion(message=ChatMessage.assistant(content, tool_calls=tool_calls))

    def function_token_reserve(self, *args, **kwargs):
        return 0  # wahoo we hardcode the prompt in the user message

    async def close(self):
        return await self.engine.close()


class WikipediaKani(Kani):
    def __init__(self, *args, question: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        self.max_search_tokens = self.engine.max_context_size // 2

    @ai_function()
    def search(self, query: str):
        """Search Wikipedia for an article with the given title, and get its content. If no such article is found, return similar article names."""
        try:
            page = DatedPage(wikipedia, title=query, redirect=True, preload=False)
        except mediawiki.PageError:
            similar = wikipedia.search(query)
            similar_searches = "\n".join(f"<search>{title}</search>" for title in similar)
            return f"No page with that title exists. Try one of the similar searches:\n{similar_searches}"
        except mediawiki.DisambiguationError as e:
            similar_searches = "\n".join(f"<search>{title}</search>" for title in e.options)
            return f"That may refer to multiple pages. Select one of these pages:\n{similar_searches}"
        else:
            corpus = Corpus([{"title": page.title, "pageid": page.pageid}], doc_len=1024)
            # retrieve as many fragments as fit in the context window
            retrieved_docs = []
            prompt = f"<document>\n<title>{page.title}</title>\n{{}}</document>"
            for doc in corpus.best(self.question):
                formatted = f"<fragment>\n{doc.content}\n</fragment>\n"
                content = prompt.format("".join(retrieved_docs) + formatted)
                doc_len = self.engine.message_len(ChatMessage.user(content))
                if doc_len > self.max_search_tokens:
                    break
                retrieved_docs.append(formatted)
            return prompt.format("".join(retrieved_docs))


# ==== main ====
async def main():
    args = parser.parse_args()
    if args.model.startswith("gpt"):
        runner = OpenAIOpenBookRunner(bench_setting="openbook", **argstokwargs(args))
    else:
        runner = OpenBookRunner(bench_setting="openbook", **argstokwargs(args))
        runner.engine = SearchEngine(runner.engine, strict=True)
    runner.load()
    await runner.run(kani_cls=WikipediaKani)
    await runner.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
