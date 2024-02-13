import hashlib
import os

from kani import Kani
from kani.engines.openai import OpenAIEngine

from fanoutqa.eval.utils import str_answer
from fanoutqa.models import DevQuestion
from fanoutqa.utils import CACHE_DIR

LLM_CACHE_DIR = CACHE_DIR / "llmcache"
LLM_CACHE_DIR.mkdir(exist_ok=True)
OPENAI_API_KEY = os.getenv("FANOUTQA_OPENAI_API_KEY", "")

engine = OpenAIEngine(api_key=OPENAI_API_KEY, model="gpt-4-0613", temperature=0, seed=31415)
factuality_system = "You are comparing a submitted answer to an expert answer on a given question."


def factuality_prompt(question: str, reference: str, answer: str):
    return (
        f"[BEGIN DATA]\n************\n[Question]: {question}\n************\n[Expert]:"
        f" {reference}\n************\n[Submission]: {answer}\n************\n[END DATA]\n\nCompare the factual content"
        " of the submitted answer with the expert answer. Ignore any differences in style, grammar, or"
        " punctuation.\nThe submitted answer may either be a subset or superset of the expert answer, or it may"
        " conflict with it. Determine which case applies. First, write out in a step by step manner your reasoning"
        " about the factual content to be sure that your conclusion is correct. Avoid simply stating the correct"
        ' answers at the outset. Then print only the single character "A", "B", "C", "D", "E", or "F" (without quotes'
        " or punctuation) on its own line corresponding to the correct answer. At the end, repeat just the letter"
        " again by itself on a new line.\n(A) The submitted answer is a subset of the expert answer and is fully"
        " consistent with it.\n(B) The submitted answer is a superset of the expert answer and is fully consistent"
        " with it.\n(C) The submitted answer contains all the same details as the expert answer.\n(D) There is a"
        " disagreement between the submitted answer and the expert answer.\n(E) The answers differ, but these"
        " differences don't matter from the perspective of factuality.\n(F) The submitted answer does not answer the"
        " question or is otherwise invalid."
    )


async def get_llm_factuality(question: DevQuestion, answer: str, cache_key=None):
    """Query GPT-4 to determine the factual equivalence of the generated answer and reference answer."""
    # cache
    if cache_key:
        ans_hash = hashlib.sha256(answer.encode()).hexdigest()[:8]
        cache_filename = LLM_CACHE_DIR / f"factual-{cache_key}-{question.id}-{ans_hash}.txt"
        if cache_filename.exists():
            return cache_filename.read_text()

    # ask the LLM if it is subjective
    prompt = factuality_prompt(question.question, str_answer(question.answer), answer)
    ai = Kani(engine, system_prompt=factuality_system)
    resp = await ai.chat_round_str(prompt)

    if cache_key:
        # noinspection PyUnboundLocalVariable
        cache_filename.write_text(resp)
    return resp
