import asyncio
import hashlib
import json
import os
import traceback
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

import fanoutqa
from fanoutqa.eval.scorer import Scorer

# prevent manipulation of results - the results must be generated by this script or else the hash will not match
LEADERBOARD_SALT = os.getenv("LEADERBOARD_SALT", "supersecret").encode()
SUBMISSIONS_ROOT = Path(__file__).parent
METADATA_PATH = SUBMISSIONS_ROOT / "metadata"
RESULTS_IN_PATH = SUBMISSIONS_ROOT / "pr-results"
RESULTS_OUT_PATH = SUBMISSIONS_ROOT / "results"
CB_PATH = SUBMISSIONS_ROOT / "closedbook-generations"
OB_PATH = SUBMISSIONS_ROOT / "openbook-generations"
EP_PATH = SUBMISSIONS_ROOT / "evidenceprovided-generations"


# ==== types ====
@dataclass
class SubmissionMetadata:
    name: str
    authors: str
    url: Optional[str]
    citation: str
    type: Literal["FOUNDATION", "FINETUNE", "PROMPT", "OTHER"]
    context: int
    is_trained_for_function_calling: bool
    closedbook_generations: Optional[str]
    openbook_generations: Optional[str]
    evidenceprovided_generations: Optional[str]
    details: Optional[str] = None


CheckResult = namedtuple("CheckResult", "metadata needs_eval submission_hash")


# ==== utils ====
def read_jsonl_answers(fp: Path) -> List[dict]:
    """Given a path to a JSONL file, return a list of the answers in that file."""
    answers = []
    with open(fp) as f:
        for ln in f:
            if not ln:
                continue
            ans = json.loads(ln)
            assert "id" in ans, "All generated answers must contain the 'id' key"
            assert "answer" in ans, "All generated answers must contain the 'answer' key"
            assert isinstance(ans["answer"], str), "All generated answers must be strings"
            answers.append(ans)
    return answers


# ==== main ====
async def hydrate_all():
    """Main entrypoint - ensure all metadata submissions have valid associated results files"""
    exit_code = 0
    written_files = []
    # for each submission file,
    for metadata_fp in METADATA_PATH.glob("*.json"):
        # check if it is valid and needs eval
        try:
            check_result = check_submission(metadata_fp)
        except Exception as e:
            # if invalid, log a check annotation and mark job failure
            print(f"::error file={metadata_fp},title=Invalid metadata file::{e}")
            exit_code = 1
            continue

        # if valid and needs eval, run the eval
        if not check_result.needs_eval:
            continue
        print(f"Found submission for {check_result.metadata.name} at {metadata_fp.name} that requires eval!")
        if check_result.metadata.closedbook_generations is not None:
            print(f"Closed-book generations path: {CB_PATH / check_result.metadata.closedbook_generations}")
        if check_result.metadata.openbook_generations is not None:
            print(f"Open-book generations path: {OB_PATH / check_result.metadata.openbook_generations}")
        if check_result.metadata.evidenceprovided_generations is not None:
            print(f"Evidence-provided generations path: {EP_PATH / check_result.metadata.evidenceprovided_generations}")
        try:
            result_fp = await eval_submission(metadata_fp, check_result)
            written_files.append(result_fp)
        except Exception as e:
            # if invalid, log a check annotation and mark job failure
            print(f"::error file={metadata_fp},title=Could not eval submission::{e}")
            traceback.print_exc()
            exit_code = 1

    print(f"Done. Wrote {len(written_files)} results files.")

    # write the written results files to GH outputs
    if "GITHUB_OUTPUT" in os.environ:
        written_files_list = " ".join(f'"{fp.absolute()}"' for fp in written_files)
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={len(written_files)}\n")
            f.write(f"written-results={written_files_list}\n")
    return exit_code


def check_submission(metadata_fp: Path) -> CheckResult:
    """Given a path to a submission metadata file, check if its corresponding results file needs to be regened.

    If exception raised, the input file(s) is/are somehow invalid; log it and continue but don't run evals
    """
    submission_name = metadata_fp.name
    # hash the submission
    the_hash = hashlib.sha256()
    the_hash.update(submission_name.encode())
    the_hash.update(metadata_fp.read_bytes())

    # ensure the metadata is readable and has all the required properties
    with open(metadata_fp) as f:
        metadata_data = json.load(f)
        metadata_data = SubmissionMetadata(**metadata_data)

    # ensure the submission files exist
    # hash the submission files
    if metadata_data.closedbook_generations is not None:
        cb_fp = CB_PATH / metadata_data.closedbook_generations
        the_hash.update(cb_fp.read_bytes())
    if metadata_data.openbook_generations is not None:
        ob_fp = OB_PATH / metadata_data.openbook_generations
        the_hash.update(ob_fp.read_bytes())
    if metadata_data.evidenceprovided_generations is not None:
        ep_fp = EP_PATH / metadata_data.evidenceprovided_generations
        the_hash.update(ep_fp.read_bytes())

    # salt the hash
    the_hash.update(LEADERBOARD_SALT)

    # check if a results file exists with that hash
    result_fp = RESULTS_IN_PATH / submission_name
    if result_fp.exists():
        with open(result_fp) as f:
            try:
                result_data = json.load(f)
                result_hash = result_data["_submission_hash"]
                # result file exists and hash matches
                if result_hash == the_hash.hexdigest():
                    # if so, no eval needed!
                    return CheckResult(metadata_data, False, the_hash)
            except (ValueError, KeyError):
                return CheckResult(metadata_data, True, the_hash)
    return CheckResult(metadata_data, True, the_hash)


async def eval_submission(metadata_fp: Path, check_result: CheckResult):
    """Read in the answers and generations and eval them all, then write the results file."""
    # dummy = {
    #     "acc": {"loose": 0.0, "strict": 0.0},
    #     "rouge": {
    #         "rouge1": {"precision": 0.0, "recall": 0.0, "fscore": 0.0},
    #         "rouge2": {"precision": 0.0, "recall": 0.0, "fscore": 0.0},
    #         "rougeL": {"precision": 0.0, "recall": 0.0, "fscore": 0.0},
    #     },
    #     "bleurt": 0.0,
    #     "gpt": 0.0,
    # }
    # closedbook_results = openbook_results = evidenceprovided_results = dummy

    questions = fanoutqa.load_dev("fanoutqa-test-answers.json")

    if check_result.metadata.closedbook_generations is not None:
        print("Evaluating closed book answers...")
        closedbook_answers = read_jsonl_answers(CB_PATH / check_result.metadata.closedbook_generations)
        closedbook_scorer = Scorer(questions, closedbook_answers, llm_cache_key="eval")
        closedbook_results = (await closedbook_scorer.score()).to_dict()
    else:
        closedbook_results = None

    if check_result.metadata.openbook_generations is not None:
        print("Evaluating open book answers...")
        openbook_answers = read_jsonl_answers(OB_PATH / check_result.metadata.openbook_generations)
        openbook_scorer = Scorer(questions, openbook_answers, llm_cache_key="eval")
        openbook_results = (await openbook_scorer.score()).to_dict()
    else:
        openbook_results = None

    if check_result.metadata.evidenceprovided_generations is not None:
        print("Evaluating evidence provided answers...")
        evidenceprovided_answers = read_jsonl_answers(EP_PATH / check_result.metadata.evidenceprovided_generations)
        evidenceprovided_scorer = Scorer(questions, evidenceprovided_answers, llm_cache_key="eval")
        evidenceprovided_results = (await evidenceprovided_scorer.score()).to_dict()
    else:
        evidenceprovided_results = None

    # hash the results to prevent score manipulation
    results_hash = hashlib.sha256()
    results_hash.update(check_result.submission_hash.hexdigest().encode())
    results_hash.update(str(closedbook_results).encode())
    results_hash.update(str(openbook_results).encode())
    results_hash.update(str(evidenceprovided_results).encode())
    results_hash.update(LEADERBOARD_SALT)

    result = {
        # SHA256(md_filename, md_content, cb_content, ob_content, ep_content, salt)
        "_submission_hash": check_result.submission_hash.hexdigest(),
        # SHA256(_submission_hash, cb_results, ob_results, ep_results, salt)
        "_results_hash": results_hash.hexdigest(),
        # metadata
        "metadata": {
            "name": check_result.metadata.name,
            "authors": check_result.metadata.authors,
            "url": check_result.metadata.url,
            "citation": check_result.metadata.citation,
            "type": check_result.metadata.type,
            "context": check_result.metadata.context,
            "is_trained_for_function_calling": check_result.metadata.is_trained_for_function_calling,
            "details": check_result.metadata.details,
        },
        # results
        "closedbook": closedbook_results,
        "openbook": openbook_results,
        "evidenceprovided": evidenceprovided_results,
    }

    result_fp = RESULTS_OUT_PATH / metadata_fp.name
    with open(result_fp, "w") as f:
        json.dump(result, f, indent=2)
    return result_fp


if __name__ == "__main__":
    ec = asyncio.run(hydrate_all())
    exit(ec)
