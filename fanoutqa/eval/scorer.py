import asyncio
import warnings
from typing import Dict, Iterable, Optional, Tuple

import rouge_score
import rouge_score.scoring
from bleurt.score import BleurtScorer
from rouge_score.rouge_scorer import RougeScorer

from fanoutqa.eval.llm import OPENAI_API_KEY, get_llm_factuality
from fanoutqa.eval.models import (
    AccuracyScore,
    Answer,
    EvaluationScore,
    EvaluationSingleScore,
    RougeScore,
    RougeScorePart,
)
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
        acc, acc_raw = self.score_accuracy()
        rouge, rouge_raw = self.score_rouge()
        bleurt_, bleurt_raw = self.score_bleurt()
        # require FANOUTQA_OPENAI_API_KEY to be set to do GPT judge to prevent footguns
        if not OPENAI_API_KEY:
            warnings.warn(
                "No OpenAI API key found! To run GPT-as-judge scoring, set the `FANOUTQA_OPENAI_API_KEY` env var to"
                " your OpenAI API key."
            )
            gptscore = 0
            gpt_raw = {}
        else:
            gptscore, gpt_raw = await self.score_gpt()

        # collect raw aggs
        raw_scores = []
        for q, a in self.get_qa_pairs():
            raw_scores.append(
                EvaluationSingleScore(
                    question_id=q.id,
                    acc=acc_raw[q.id],
                    rouge=rouge_raw[q.id],
                    bleurt=bleurt_raw[q.id],
                    gpt=gpt_raw.get(q.id),
                )
            )
        return EvaluationScore(acc=acc, rouge=rouge, bleurt=bleurt_, gpt=gptscore, raw=raw_scores)

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
                yield q, a

    # scorers
    def score_accuracy(self) -> Tuple[AccuracyScore, Dict[str, float]]:
        """Get the loose and strict accuracy scores for the loaded qs and as."""
        raw_scores = {}  # qid -> score
        accs = []
        n_perfect = 0
        for q, a in self.get_qa_pairs():
            if a is None:
                accs.append(0)
                raw_scores[q.id] = 0
                continue
            result = answer_in_text(q.answer, a["answer"])
            accs.append(result.score)
            raw_scores[q.id] = result.score
            if result.found:
                n_perfect += 1

        assert len(accs) == self.eval_len
        assert len(raw_scores) == self.eval_len
        avg_acc = sum(accs) / self.eval_len
        pct_perfect = n_perfect / self.eval_len
        return AccuracyScore(loose=avg_acc, strict=pct_perfect), raw_scores

    def score_rouge(self) -> Tuple[RougeScore, Dict[str, RougeScore]]:
        """Get the ROUGE-1, ROUGE-2, and ROUGE-L scores (P/R/F1) for the loaded qs and as."""
        raw_scores = {}  # qid -> RougeScore
        scores = {t: [] for t in ROUGE_TYPES}  # rouge_type -> list[Score]
        for q, a in self.get_qa_pairs():
            if a is None:
                for score in scores.values():
                    score.append(rouge_score.scoring.Score(0, 0, 0))
                raw_scores[q.id] = RougeScore(
                    **{k: RougeScorePart(precision=0, recall=0, fscore=0) for k in ROUGE_TYPES}
                )
                continue
            results = self.rouge.score(str_answer(q.answer), str_answer(a["answer"]))
            for k, v in results.items():
                scores[k].append(v)
            raw_scores[q.id] = RougeScore(
                **{
                    k: RougeScorePart(precision=v.precision, recall=v.recall, fscore=v.fmeasure)
                    for k, v in results.items()
                }
            )

        assert all(len(v) == self.eval_len for v in scores.values())
        assert len(raw_scores) == self.eval_len
        out = {}
        for k, v in scores.items():
            avg_precision = sum(s.precision for s in v) / self.eval_len
            avg_recall = sum(s.recall for s in v) / self.eval_len
            avg_fscore = sum(s.fmeasure for s in v) / self.eval_len
            out[k] = RougeScorePart(precision=avg_precision, recall=avg_recall, fscore=avg_fscore)
        return RougeScore(**out), raw_scores

    def score_bleurt(self) -> Tuple[float, Dict[str, float]]:
        """Get the BLEURT score for the loaded qs and as."""
        references = []
        candidates = []
        idx_to_id = {}
        for idx, (q, a) in enumerate(self.get_qa_pairs()):
            idx_to_id[idx] = q.id
            if a is None:
                candidates.append("")
            else:
                candidates.append(str_answer(a["answer"]))
            references.append(str_answer(q.answer))

        scores = self.bleurt.score(references=references, candidates=candidates)
        assert len(scores) == self.eval_len
        avg_score = sum(scores) / self.eval_len
        raw_scores = {idx_to_id[idx]: score for idx, score in enumerate(scores)}
        assert len(raw_scores) == self.eval_len
        return avg_score, raw_scores

    async def score_gpt(self) -> Tuple[float, Dict[str, int]]:
        """Use GPT-4 as a judge to grade the loaded qs and as."""
        accs = []
        raw_scores = {}

        for batch in batched(self.get_qa_pairs(), 20):
            # eval 20 qs at a time
            coros = []
            ids = []
            for q, a in batch:
                if a is None:
                    accs.append(0)
                    raw_scores[q.id] = 0
                    continue
                # sometimes we have fun neural text degeneration, just cut it off
                ans = a["answer"]
                if len(a["answer"]) > 4000:
                    warnings.warn(f"The answer to question ID {a['id']} is too long, trimming it to 4000 characters.")
                    ans = ans[:4000]
                coro = get_llm_factuality(q, ans, cache_key=self.llm_cache_key)
                coros.append(coro)
                ids.append(q.id)

            # and score their answers
            # B, C, E = full score, anything else = 0
            answers = await asyncio.gather(*coros)
            for qid, result in zip(ids, answers):
                mc = result.strip()[-1].lower()
                if mc in "bce":
                    accs.append(1)
                    raw_scores[qid] = 1
                else:
                    accs.append(0)
                    raw_scores[qid] = 0

        assert len(accs) == self.eval_len
        assert len(raw_scores) == self.eval_len
        avg_acc = sum(accs) / self.eval_len
        return avg_acc, raw_scores


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
