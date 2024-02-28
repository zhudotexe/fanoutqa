"""Output 10 questions for the human eval."""

import random

from bench.utils import REPO_ROOT, load_questions


def main():
    qs = load_questions(REPO_ROOT / "fanout-final-dev.json")
    for i, q in enumerate(random.sample(qs, 10)):
        print(f"**Question {i + 1} ({q['id']})**: {q['question']}")


if __name__ == "__main__":
    main()
