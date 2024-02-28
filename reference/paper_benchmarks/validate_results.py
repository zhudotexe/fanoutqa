"""
Ensure that each result has all of the answers for the test set.
Write the IDs of the missing configurations to config/{model}-{setting}.txt, one per line
"""

import json
from pathlib import Path

from bench.utils import REPO_ROOT, load_questions, load_results


def fix_one(fp: Path):
    fn = fp.stem
    prompt_file = open(REPO_ROOT / f"results/prompts-{fn}.json", "w")
    results_file = open(REPO_ROOT / f"results/results-{fn}.jsonl", "w")
    extras_file = open(REPO_ROOT / f"results/extra-{fn}.jsonl", "w")

    with open(fp) as f:
        data = json.load(f)

    prompts = []
    for result in data:
        smol = {"id": result["id"], "answer": result["answer"], "question": result["question"]}
        results_file.write(json.dumps(smol))
        results_file.write("\n")
        # extras
        extras_file.write(json.dumps(result))
        extras_file.write("\n")
        # prompts
        prompts.append({"id": result["id"], "prompt": result["prompt"]})

    json.dump(prompts, prompt_file)

    prompt_file.close()
    results_file.close()
    extras_file.close()


def validate(questions, results) -> list[str]:
    """Given the questions and results, output a list of missing IDs"""
    question_ids_list = [q["id"] for q in questions]
    question_ids = set(q["id"] for q in questions)
    result_ids = set(r["id"] for r in results if r["answer"])
    return sorted(question_ids.difference(result_ids), key=lambda i: question_ids_list.index(i))


def validate_one(questions, fp):
    fn = fp.stem.removeprefix("results-")
    results = load_results(fp)
    missing = validate(questions, results)
    with open(REPO_ROOT / f"config/{fn}.txt", "w") as f:
        f.write("\n".join(missing))
    print(f"{fp}: {len(questions) - len(missing)} / {len(questions)}")
    # remove the ones that errored
    with open(fp, "w") as f:
        for r in results:
            if not r["answer"]:
                continue
            f.write(json.dumps(r))
            f.write("\n")


def main():
    questions = load_questions()
    # for result_path in (REPO_ROOT / "results-old").glob("*.json"):
    #     fix_one(result_path)

    for result_path in (REPO_ROOT / "results").glob("results-*.jsonl"):
        validate_one(questions, result_path)


if __name__ == "__main__":
    main()
