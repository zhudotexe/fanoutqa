import itertools
import re
from collections import namedtuple

from fanoutqa.models import AnswerType
from fanoutqa.norm import normalize

AccuracyResult = namedtuple("AccuracyResult", "found score missing")


def answer_in_text(reference: AnswerType, candidate: str) -> AccuracyResult:
    """What proportion of answer strings found in the reference can also be found in the candidate?"""
    if isinstance(reference, list):
        missing = []
        for a in reference:
            result = answer_in_text(a, candidate)
            missing.extend(result.missing)
        n_found = len(reference) - len(missing)
        return AccuracyResult(found=n_found == len(reference), score=n_found / len(reference), missing=missing)
    elif isinstance(reference, dict):
        missing = []
        vals = itertools.chain(reference.keys(), reference.values())
        for a in vals:
            result = answer_in_text(a, candidate)
            missing.extend(result.missing)
        n_ref = len(reference) * 2
        n_found = n_ref - len(missing)  # kvs
        return AccuracyResult(found=n_found == n_ref, score=n_found / n_ref, missing=missing)
    else:
        if isinstance(reference, bool):
            reference = "yes" if reference else "no"
        # primitive
        norm_ans = normalize(reference)
        norm_cand = normalize(candidate)
        # ensure the answer is surrounded by word boundaries
        if not re.search(rf"\b{re.escape(norm_ans)}\b", norm_cand):
            return AccuracyResult(found=False, score=0, missing=[norm_ans])
    return AccuracyResult(found=True, score=1, missing=[])
