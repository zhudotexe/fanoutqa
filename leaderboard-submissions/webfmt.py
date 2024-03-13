"""Copy the results in leaderboard-submissions/results/ to leaderboard/src/data in the expected format for the web."""

import json
from pathlib import Path

SUBMISSIONS_ROOT = Path(__file__).parent
REPO_ROOT = SUBMISSIONS_ROOT.parent
METADATA_PATH = SUBMISSIONS_ROOT / "metadata"
RESULTS_PATH = SUBMISSIONS_ROOT / "results"
WEB_DATA_PATH = REPO_ROOT / "leaderboard/src/data"


def main():
    results_closed = []
    results_open = []
    results_provided = []

    for fp in RESULTS_PATH.glob("*.json"):
        with open(fp) as f:
            result = json.load(f)

        cb = {**result["metadata"], **result["closedbook"]}
        ob = {**result["metadata"], **result["openbook"]}
        ep = {**result["metadata"], **result["evidenceprovided"]}

        results_closed.append(cb)
        results_open.append(ob)
        results_provided.append(ep)

    with open(WEB_DATA_PATH / "web-closedbook.json", "w") as f:
        json.dump(results_closed, f, indent=2)
    with open(WEB_DATA_PATH / "web-openbook.json", "w") as f:
        json.dump(results_open, f, indent=2)
    with open(WEB_DATA_PATH / "web-wiki-provided.json", "w") as f:
        json.dump(results_provided, f, indent=2)


if __name__ == "__main__":
    main()
