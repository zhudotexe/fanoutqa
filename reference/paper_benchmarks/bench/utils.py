import json
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def load_questions(fp: Path = None):
    if fp is None:
        fp = REPO_ROOT / "fanout-final-test.json"
    with open(fp) as f:
        return json.load(f)


def load_results(fp: Path):
    """Load results from a jsonl file"""
    results = []
    with open(fp) as f:
        for line in f:
            results.append(json.loads(line))
    return results
