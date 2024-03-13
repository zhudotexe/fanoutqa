"""Given a list of newly-written results files as argv, output a nice little Markdown summary of them."""

import json
import os
import sys

RUN_LINK = os.getenv("RUN_LINK")

print(f"Eval run succeeded! Link to run: [link]({RUN_LINK})\n\nHere are the results of the submission(s):\n")

for fp in sys.argv[1:]:
    with open(fp) as f:
        results = json.load(f)

    cb = results["closedbook"]
    ob = results["openbook"]
    ep = results["evidenceprovided"]

    print(
        f"# {results['name']}\n"
        f"*[{results['citation']}]({results['url']})*\n\n"
        "## Closed Book\n\n"
        f"- **Loose**: {cb['acc']['loose']:.3}\n"
        f"- **Strict**: {cb['acc']['strict']:.3}\n"
        f"- **ROUGE-1**: {cb['rouge']['rouge1']['fscore']:.3}\n"
        f"- **ROUGE-2**: {cb['rouge']['rouge2']['fscore']:.3}\n"
        f"- **ROUGE-L**: {cb['rouge']['rougeL']['fscore']:.3}\n"
        f"- **BLEURT**: {cb['bleurt']:.3}\n"
        f"- **GPT Judge**: {cb['gpt']:.3}\n\n"
        "## Open Book\n\n"
        f"- **Loose**: {ob['acc']['loose']:.3}\n"
        f"- **Strict**: {ob['acc']['strict']:.3}\n"
        f"- **ROUGE-1**: {ob['rouge']['rouge1']['fscore']:.3}\n"
        f"- **ROUGE-2**: {ob['rouge']['rouge2']['fscore']:.3}\n"
        f"- **ROUGE-L**: {ob['rouge']['rougeL']['fscore']:.3}\n"
        f"- **BLEURT**: {ob['bleurt']:.3}\n"
        f"- **GPT Judge**: {ob['gpt']:.3}\n\n"
        "## Evidence Provided\n\n"
        f"- **Loose**: {ep['acc']['loose']:.3}\n"
        f"- **Strict**: {ep['acc']['strict']:.3}\n"
        f"- **ROUGE-1**: {ep['rouge']['rouge1']['fscore']:.3}\n"
        f"- **ROUGE-2**: {ep['rouge']['rouge2']['fscore']:.3}\n"
        f"- **ROUGE-L**: {ep['rouge']['rougeL']['fscore']:.3}\n"
        f"- **BLEURT**: {ep['bleurt']:.3}\n"
        f"- **GPT Judge**: {ep['gpt']:.3}\n"
    )

print(
    "If all looks well, a maintainer will come by soon to merge this PR and your entry/entries will appear on the"
    " leaderboard. If you need to make any changes, feel free to push new commits to this PR. Thanks for submitting to"
    " FanOutQA!"
)
