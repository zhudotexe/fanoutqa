"""Read all the scores and output them as CSV so I don't have to type them all."""

import json

from bench.utils import REPO_ROOT

settings = ["closedbook", "openbook", "wiki-provided"]
model_info = {
    "gpt-4": {
        "name": "GPT-4",
        "authors": "OpenAI",
        "url": "https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo",
        "citation": "OpenAI, 2023",
        "type": "FOUNDATION",
        "context": 8192,
    },
    "gpt-4-turbo": {
        "name": "GPT-4-turbo",
        "authors": "OpenAI",
        "url": "https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo",
        "citation": "OpenAI, 2023",
        "type": "FOUNDATION",
        "context": 128000,
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5-turbo",
        "authors": "OpenAI",
        "url": "https://platform.openai.com/docs/models/gpt-3-5-turbo",
        "citation": "OpenAI, 2023",
        "type": "FOUNDATION",
        "context": 16384,
    },
    "llama-chat": {
        "name": "LLaMA 2 70B",
        "authors": "Meta",
        "url": "https://ai.meta.com/research/publications/llama-2-open-foundation-and-fine-tuned-chat-models/",
        "citation": "Touvron et al., 2023",
        "type": "FOUNDATION",
        "context": 4096,
    },
    "mistral-chat": {
        "name": "Mistral-7B",
        "authors": "Mistral AI",
        "url": "https://mistral.ai/news/announcing-mistral-7b/",
        "citation": "Jiang et al., 2023",
        "type": "FOUNDATION",
        "context": 32000,
    },
    "mixtral": {
        "name": "Mixtral-8x7B",
        "authors": "Mistral AI",
        "url": "https://mistral.ai/news/mixtral-of-experts/",
        "citation": "Jiang et al., 2024",
        "type": "FOUNDATION",
        "context": 32000,
    },
    "claude": {
        "name": "Claude 2.1",
        "authors": "Anthropic",
        "url": "https://www.anthropic.com/news/claude-2-1",
        "citation": "Anthropic, 2023",
        "type": "FOUNDATION",
        "context": 200000,
    },
}

for setting in settings:
    results = []
    for model, info in model_info.items():
        result_path = REPO_ROOT / f"results/score-{setting}-{model}.json"
        with open(result_path) as f:
            scores = json.load(f)
        scores["rouge"].pop("rougeLsum", None)
        scores["acc"]["loose"] = scores["acc"].pop("acc")
        scores["acc"]["strict"] = scores["acc"].pop("perfect")
        scores.update(info)
        results.append(scores)

    with open(REPO_ROOT / f"results/web-{setting}.json", "w") as f:
        json.dump(results, f)
