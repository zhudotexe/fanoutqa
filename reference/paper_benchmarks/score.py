import asyncio
import hashlib
import json
import re
from pathlib import Path

import rouge_score.scoring
import tqdm
from bleurt.score import BleurtScorer
from kani import Kani
from kani.engines.openai import OpenAIEngine
from rouge_score.rouge_scorer import RougeScorer

from bench.score import answer_in_text, str_answer
from bench.utils import REPO_ROOT, load_questions, load_results
from fanout.utils import batched

rouge_types = ["rouge1", "rouge2", "rougeL", "rougeLsum"]
# ===== llm =====
LLM_CACHE_DIR = REPO_ROOT / ".llmcache"
LLM_CACHE_DIR.mkdir(exist_ok=True)
engine = OpenAIEngine(model="gpt-4-0613", temperature=0, seed=31415)
factuality_system = "You are comparing a submitted answer to an expert answer on a given question."


def factuality_prompt_old(question, reference, answer):
    return (
        f"[BEGIN DATA]\n************\n[Question]: {question}\n************\n[Expert]:"
        f" {reference}\n************\n[Submission]: {answer}\n************\n[END DATA]\n\nCompare the factual content"
        " of the submitted answer with the expert answer. Ignore any differences in style, grammar, or"
        " punctuation.\nThe submitted answer may either be a subset or superset of the expert answer, or it may"
        " conflict with it. Determine which case applies. First, write out in a step by step manner your reasoning"
        " about the factual content to be sure that your conclusion is correct. Avoid simply stating the correct"
        ' answers at the outset. Then print only the single character "A", "B", "C", "D", or "E" (without quotes'
        " or punctuation) on its own line corresponding to the correct answer. At the end, repeat just the letter"
        " again by itself on a new line.\n(A) The submitted answer is a subset of the expert answer and is fully"
        " consistent with it.\n(B) The submitted answer is a superset of the expert answer and is fully consistent"
        " with it.\n(C) The submitted answer contains all the same details as the expert answer.\n(D) There is a"
        " disagreement between the submitted answer and the expert answer.\n(E) The answers differ, but these"
        " differences don't matter from the perspective of factuality."
    )


def factuality_prompt(question, reference, answer):
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


class Scorer:
    def __init__(self, results, key, questions=None, only_score_answered=False):
        self.key = key
        self.only_score_answered = only_score_answered
        self.questions = questions or load_questions()
        self.questions_by_id = {q["id"]: q for q in self.questions}
        self.results = results
        self.results_by_id = {r["id"]: r for r in self.results}
        self.rouge = RougeScorer(rouge_types, use_stemmer=True)
        self.bleurt = BleurtScorer("BLEURT-20")
        # number of trials to eval
        if self.only_score_answered:
            self.eval_len = len(self.results)
        else:
            self.eval_len = len(self.questions)

    @classmethod
    def from_fp(cls, fp: Path, questions):
        results = load_results(fp)
        return cls(results=results, key=fp.stem.removeprefix("results-"), questions=questions)

    async def score(self):
        acc = self.score_accuracy()
        rouge = self.score_rouge()
        bleurt_ = self.score_bleurt()
        gptscore = await self.score_gpt()
        data = {"acc": acc, "rouge": rouge, "bleurt": bleurt_, "gpt": gptscore}
        with open(REPO_ROOT / f"results/score-{self.key}.json", "w") as f:
            json.dump(data, f, indent=2)

    def get_qa_pairs(self):
        if self.only_score_answered:
            for a in tqdm.tqdm(self.results):
                q = self.questions_by_id.get(a["id"])
                yield q, a
        else:
            for q in tqdm.tqdm(self.questions):
                a = self.results_by_id.get(q["id"])
                if a is None:
                    yield None, None
                yield q, a

    def score_accuracy(self):
        accs = []
        n_perfect = 0
        for q, a in self.get_qa_pairs():
            if a is None:
                accs.append(0)
                continue
            result = answer_in_text(q["answer"], a["answer"])
            accs.append(result.score)
            if result.found:
                n_perfect += 1

        assert len(accs) == self.eval_len
        avg_acc = sum(accs) / self.eval_len
        pct_perfect = n_perfect / self.eval_len
        print(f"AVG ACC: {avg_acc}")
        print(f"PCT PFT: {pct_perfect}")
        return {"acc": avg_acc, "perfect": pct_perfect}

    def score_rouge(self):
        scores = {t: [] for t in rouge_types}
        for q, a in self.get_qa_pairs():
            if a is None:
                for score in scores.values():
                    score.append(rouge_score.scoring.Score(0, 0, 0))
                continue
            results = self.rouge.score(str_answer(q["answer"]), str_answer(a["answer"]))
            for k, v in results.items():
                scores[k].append(v)

        assert all(len(v) == self.eval_len for v in scores.values())
        print("=== ROUGE ===")
        out = {}
        for k, v in scores.items():
            print(f"--- {k} ---")
            avg_precision = sum(s.precision for s in v) / self.eval_len
            avg_recall = sum(s.recall for s in v) / self.eval_len
            avg_fscore = sum(s.fmeasure for s in v) / self.eval_len
            print(f"precision: {avg_precision}")
            print(f"recall: {avg_recall}")
            print(f"fscore: {avg_fscore}")
            out[k] = {"precision": avg_precision, "recall": avg_recall, "fscore": avg_fscore}
        print()
        return out

    def score_bleurt(self):
        references = []
        candidates = []
        for q, a in self.get_qa_pairs():
            if a is None:
                candidates.append("")
            else:
                candidates.append(str_answer(a["answer"]))
            references.append(str_answer(q["answer"]))

        scores = self.bleurt.score(references=references, candidates=candidates)
        assert len(scores) == self.eval_len
        avg_score = sum(scores) / self.eval_len
        print(f"BLEURT: {avg_score}")
        return avg_score

    async def score_gpt(self):
        accs = []

        for pairs in batched(self.get_qa_pairs(), 20):
            # eval 20 qs at a time
            coros = []
            for q, a in pairs:
                if a is None:
                    accs.append(0)
                    continue
                # sometimes we have fun neural text degeneration, just cut it off
                ans = a["answer"][:4000]
                coro = self.get_llm_factuality(q, ans)
                coros.append(coro)

            # and score their answers
            # B, C, E = full score, anything else = 0
            answers = await asyncio.gather(*coros)
            for result in answers:
                mc = result.strip()[-1].lower()
                if mc in "bce":
                    accs.append(1)
                else:
                    accs.append(0)

        assert len(accs) == self.eval_len
        avg_acc = sum(accs) / self.eval_len
        print(f"GPT ACC: {avg_acc}")
        return avg_acc

    async def get_llm_factuality(self, question, answer):
        # cache
        ans_hash = hashlib.sha256(answer.encode()).hexdigest()[:8]
        cache_filename = LLM_CACHE_DIR / f"factual-{self.key}-{question['id']}-{ans_hash}.txt"
        if cache_filename.exists():
            return cache_filename.read_text()

        # ask the LLM if it is subjective
        prompt = factuality_prompt(question["question"], str_answer(question["answer"]), answer)
        ai = Kani(engine, system_prompt=factuality_system)
        resp = await ai.chat_round_str(prompt)
        cache_filename.write_text(resp)
        return resp


async def score_human():
    questions = load_questions(REPO_ROOT / "fanout-final-test-answers.json")

    # read the human responses and {id, answer} them
    results = []
    with open(REPO_ROOT / "human_responses.txt") as f:
        data = f.read()
        for segment in data.split("###SEP "):
            segment = segment.strip()
            if not segment:
                continue
            # fix some weird tokenization stuff in the human responses
            segment = segment.replace("https://en.wikipedia.org/wiki/", "").replace("_", " ")

            id_, content = segment.split("\n", 1)
            results.append({"id": id_, "answer": content})

    scorer = Scorer(results, key="human", questions=questions, only_score_answered=True)
    await scorer.score()


async def main(fps=None):
    if fps is None:
        fps = (REPO_ROOT / "results").glob("results-*.jsonl")
    questions = load_questions(REPO_ROOT / "fanout-final-test-answers.json")
    for result_path in fps:
        print(result_path.stem)
        scorer = Scorer.from_fp(result_path, questions)
        await scorer.score()


if __name__ == "__main__":
    # fps = [Path(a) for a in sys.argv[1:]]
    # asyncio.run(main(fps))
    asyncio.run(score_human())
