import asyncio
import logging

from kani import ChatMessage

from bench.runner import Runner, TOKEN_RESERVE, argstokwargs, parser
from fanout.retrieval import Corpus


class WikiProvidedRunner(Runner):
    def load(self, max_prompt_tokens):
        self.questions = self.get_questions()
        self.prompts = self.get_prompts(self.questions, max_prompt_tokens)

    # noinspection PyMethodOverriding
    def get_prompt(self, question, max_prompt_tokens) -> str:
        question_text = question["question"]

        # index all of the documents, splitting by paragraph/sentence to a max of 1024 characters
        corpus = Corpus(question["necessary_evidence"], doc_len=1024)

        # build the initial prompt
        prompt = (
            "*** BEGIN DATA ***\n\n{}\n*** END DATA ***\n\nAnswer the following question based on the documents"
            " above, and output only your answer. If the answer is a list, output one on each line. Current date:"
            f" 11-20-2023.\n\n[Question]: {question_text}"
        )

        # retrieve as many fragments as fit in the context window
        # format: <document>\n<title>{title}</title>\n<content>{content}</content>\n</document>
        retrieved_docs = []
        for doc in corpus.best(question_text):
            formatted = f"<document>\n<title>{doc.title}</title>\n<content>{doc.content}</content>\n</document>\n"
            content = prompt.format("".join(retrieved_docs) + formatted)
            doc_len = self.engine.message_len(ChatMessage.user(content))
            if doc_len > max_prompt_tokens:
                break
            retrieved_docs.append(formatted)
        prompt = prompt.format("".join(retrieved_docs))
        return prompt


async def main():
    args = parser.parse_args()
    runner = WikiProvidedRunner(bench_setting="wiki-provided", **argstokwargs(args))
    max_prompt_tokens = runner.engine.max_context_size - TOKEN_RESERVE
    print(f"Building prompts for input length {max_prompt_tokens}...")
    runner.load(max_prompt_tokens)
    print("Generating...")
    await runner.run()
    await runner.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
