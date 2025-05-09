"""Given a list of newly-written results files as argv, output a nice little Markdown summary of them."""

import json
import os
import sys

RUN_LINK = os.getenv("RUN_LINK")

print(f"Eval run succeeded! Link to run: [link]({RUN_LINK})\n\nHere are the results of the submission(s):\n")


def fmt_results(r):
    return (
        f"- **Loose**: {r['acc']['loose']:.3}\n"
        f"- **Strict**: {r['acc']['strict']:.3}\n"
        f"- **ROUGE-1**: {r['rouge']['rouge1']['fscore']:.3}\n"
        f"- **ROUGE-2**: {r['rouge']['rouge2']['fscore']:.3}\n"
        f"- **ROUGE-L**: {r['rouge']['rougeL']['fscore']:.3}\n"
        f"- **BLEURT**: {r['bleurt']:.3}\n"
        f"- **GPT Judge**: {r['gpt']:.3}"
    )


for fp in sys.argv[1:]:
    with open(fp) as f:
        results = json.load(f)

    metadata = results["metadata"]
    cb = results["closedbook"]
    ob = results["openbook"]
    ep = results["evidenceprovided"]

    print(f"# {metadata['name']}\n*[{metadata['citation']}]({metadata['url']})*\n")

    if cb is not None:
        print("## Closed Book\n")
        print(fmt_results(cb))
        print()

    if ob is not None:
        print("## Open Book\n")
        print(fmt_results(ob))
        print()

    if ep is not None:
        print("## Evidence Provided\n")
        print(fmt_results(ep))
        print()

    if cb is None and ob is None and ep is None:
        print("> [!WARNING]\n> No valid generations were found. Please check the format of your metadata file.\n")


print(
    "If all looks well, a maintainer will come by soon to merge this PR and your entry/entries will appear on the"
    " leaderboard. If you need to make any changes, feel free to push new commits to this PR. Thanks for submitting to"
    " FanOutQA!"
)
