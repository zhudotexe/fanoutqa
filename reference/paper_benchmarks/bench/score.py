import itertools
import re
from collections import namedtuple

from fanout.norm import normalize

AccuracyResult = namedtuple("AccuracyResult", "found score missing")


def answer_in_text(reference, candidate: str) -> AccuracyResult:
    """Is the answer present in the text?"""
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


def str_answer(ans) -> str:
    """Ensure the answer is a string for string-based metrics like ROUGE. Don't normalize it otherwise."""
    if isinstance(ans, list):
        return "\n".join(map(str_answer, ans))
    elif isinstance(ans, dict):
        return "\n".join(f"{k} - {str_answer(v)}" for k, v in ans.items())
    elif isinstance(ans, bool):
        return "yes" if ans else "no"
    elif ans is None:
        return ""
    return str(ans)
