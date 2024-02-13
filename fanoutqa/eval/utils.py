from fanoutqa.models import AnswerType


def str_answer(ans: AnswerType) -> str:
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
