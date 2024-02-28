"""Read all the scores and output them as CSV so I don't have to type them all."""

import json

from bench.utils import REPO_ROOT

settings = ["closedbook", "openbook", "wiki-provided"]
models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "llama-chat", "mistral-chat", "mixtral", "claude"]


def print_one(fp):
    with open(fp) as f:
        scores = json.load(f)
    acc = scores["acc"]["acc"]
    perf = scores["acc"]["perfect"]
    r1p = scores["rouge"]["rouge1"]["precision"]
    r1r = scores["rouge"]["rouge1"]["recall"]
    r1f = scores["rouge"]["rouge1"]["fscore"]
    r2p = scores["rouge"]["rouge2"]["precision"]
    r2r = scores["rouge"]["rouge2"]["recall"]
    r2f = scores["rouge"]["rouge2"]["fscore"]
    rLp = scores["rouge"]["rougeL"]["precision"]
    rLr = scores["rouge"]["rougeL"]["recall"]
    rLf = scores["rouge"]["rougeL"]["fscore"]
    bleurt = scores["bleurt"]
    gptscore = scores["gpt"]
    print(",".join(map(str, (acc, perf, r1p, r1r, r1f, r2p, r2r, r2f, rLp, rLr, rLf, bleurt, gptscore))))


for setting in settings:
    print(f"==== {setting} ====")
    for model in models:
        result_path = REPO_ROOT / f"results/score-{setting}-{model}.json"
        print(f"{model},", end="")
        print_one(result_path)
