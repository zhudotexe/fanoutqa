import asyncio
import warnings
from typing import Iterable, Optional

import rouge_score
import rouge_score.scoring
from bleurt.score import BleurtScorer
from rouge_score.rouge_scorer import RougeScorer

from fanoutqa.eval.llm import OPENAI_API_KEY, get_llm_factuality
from fanoutqa.eval.models import AccuracyScore, Answer, EvaluationScore, RougeScore, RougeScorePart
from fanoutqa.eval.string import answer_in_text
from fanoutqa.eval.utils import str_answer
from fanoutqa.models import DevQuestion
from fanoutqa.utils import batched

ROUGE_TYPES = ("rouge1", "rouge2", "rougeL")


class Scorer:
    def __init__(
        self, questions: list[DevQuestion], answers: list[Answer], only_score_answered=False, llm_cache_key: str = None
    ):
        """
        :param questions: The questions and reference answers, as loaded by the dataset
        :param answers: The generated answers to score
        :param only_score_answered: Whether to only score questions that have an answer (True), or consider unanswered
            questions to have 0 score (False, default).
        :param llm_cache_key: If this is provided, cache the LLM-as-judge generations with this key. We recommend
            setting this to a human-readable key for each system under test.
        """
        self.questions = questions
        self.questions_by_id = {q.id: q for q in self.questions}
        self.answers = answers
        self.answers_by_id = {r["id"]: r for r in self.answers}

        # number of trials to eval
        self.only_score_answered = only_score_answered
        if self.only_score_answered:
            self.eval_len = len(self.answers)
        else:
            self.eval_len = len(self.questions)

        self.llm_cache_key = llm_cache_key

        # ext evallers
        self.rouge = RougeScorer(ROUGE_TYPES, use_stemmer=True)
        self.bleurt = BleurtScorer("BLEURT-20")

    async def score(self):
        acc = self.score_accuracy()
        rouge = self.score_rouge()
        bleurt_ = self.score_bleurt()
        # require FANOUTQA_OPENAI_API_KEY to be set to do GPT judge to prevent footguns
        if not OPENAI_API_KEY:
            warnings.warn(
                "No OpenAI API key found! To run GPT-as-judge scoring, set the `FANOUTQA_OPENAI_API_KEY` env var to"
                " your OpenAI API key."
            )
            gptscore = 0
        else:
            gptscore = await self.score_gpt()
        return EvaluationScore(acc=acc, rouge=rouge, bleurt=bleurt_, gpt=gptscore)

    def get_qa_pairs(self) -> Iterable[tuple[DevQuestion, Optional[Answer]]]:
        """Yield pairs of questions and answers to score.
        The answer may be None if there is no answer for a given question and ``only_score_answered`` is False.
        """
        if self.only_score_answered:
            for a in self.answers:
                q = self.questions_by_id.get(a["id"])
                yield q, a
        else:
            for q in self.questions:
                a = self.answers_by_id.get(q.id)
                if a is None:
                    yield q, None
                yield q, a

    # scorers
    def score_accuracy(self) -> AccuracyScore:
        """Get the loose and strict accuracy scores for the loaded qs and as."""
        accs = []
        n_perfect = 0
        for q, a in self.get_qa_pairs():
            if a is None:
                accs.append(0)
                continue
            result = answer_in_text(q.answer, a["answer"])
            accs.append(result.score)
            if result.found:
                n_perfect += 1

        assert len(accs) == self.eval_len
        avg_acc = sum(accs) / self.eval_len
        pct_perfect = n_perfect / self.eval_len
        return AccuracyScore(loose=avg_acc, strict=pct_perfect)

    def score_rouge(self) -> RougeScore:
        """Get the ROUGE-1, ROUGE-2, and ROUGE-L scores (P/R/F1) for the loaded qs and as."""
        scores = {t: [] for t in ROUGE_TYPES}
        for q, a in self.get_qa_pairs():
            if a is None:
                for score in scores.values():
                    score.append(rouge_score.scoring.Score(0, 0, 0))
                continue
            results = self.rouge.score(str_answer(q.answer), str_answer(a["answer"]))
            for k, v in results.items():
                scores[k].append(v)

        assert all(len(v) == self.eval_len for v in scores.values())
        out = {}
        for k, v in scores.items():
            avg_precision = sum(s.precision for s in v) / self.eval_len
            avg_recall = sum(s.recall for s in v) / self.eval_len
            avg_fscore = sum(s.fmeasure for s in v) / self.eval_len
            out[k] = RougeScorePart(precision=avg_precision, recall=avg_recall, fscore=avg_fscore)
        return RougeScore(**out)

    def score_bleurt(self) -> float:
        """Get the BLEURT score for the loaded qs and as."""
        references = []
        candidates = []
        for q, a in self.get_qa_pairs():
            if a is None:
                candidates.append("")
            else:
                candidates.append(str_answer(a["answer"]))
            references.append(str_answer(q.answer))

        scores = self.bleurt.score(references=references, candidates=candidates)
        assert len(scores) == self.eval_len
        avg_score = sum(scores) / self.eval_len
        return avg_score

    async def score_gpt(self):
        """Use GPT-4 as a judge to grade the loaded qs and as."""
        accs = []

        for pairs in batched(self.get_qa_pairs(), 20):
            # eval 20 qs at a time
            coros = []
            for q, a in pairs:
                if a is None:
                    accs.append(0)
                    continue
                # sometimes we have fun neural text degeneration, just cut it off
                ans = a["answer"]
                if len(a["answer"]) > 4000:
                    warnings.warn(f"The answer to question ID {a['id']} is too long, trimming it to 4000 characters.")
                    ans = ans[:4000]
                coro = get_llm_factuality(q, ans, cache_key=self.llm_cache_key)
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
        return avg_acc


def evaluate(questions: list[DevQuestion], answers: list[Answer], **kwargs) -> EvaluationScore:
    """
    Evaluate all FOQA metrics across the given questions and generated answers.

    :param questions: The questions and reference answers, as loaded by the dataset.
    :param answers: The generated answers to score. These should be dictionaries like ``{"id": "...", "answer": "..."}``
    :param only_score_answered: Whether to only score questions that have an answer (True), or consider unanswered
        questions to have 0 score (False, default). This is useful for evaluating only a subset of the dataset.
    :param llm_cache_key: If this is provided, cache the LLM-as-judge generations with this key. We recommend
        setting this to a human-readable key for each system under test.
    """
    scorer = Scorer(questions, answers, **kwargs)
    return asyncio.run(scorer.score())
