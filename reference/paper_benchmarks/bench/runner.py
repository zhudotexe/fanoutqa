import argparse
import asyncio
import json
import logging
from collections import namedtuple

import tqdm
from kani import Kani

from bench.engines import can_parallel, get_engine
from bench.utils import REPO_ROOT, load_questions
from fanout.utils import batched

parser = argparse.ArgumentParser()
parser.add_argument(
    "-m",
    "--model",
    choices=[
        "gpt-4",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "llama-chat",
        "mistral-chat",
        "mixtral",
        "longllama",
        "claude",
    ],
    required=True,
)
parser.add_argument("-n", "--count", type=int, default=None)
parser.add_argument("--ignore-config", type=bool, default=False)
parser.add_argument("--no-cache-prompt", type=bool, default=False)
parser.add_argument("--ctx-size", type=int, default=None)


def argstokwargs(args):
    return dict(
        model_name=args.model,
        n_questions=args.count,
        ignore_config=args.ignore_config,
        no_cache_prompt=args.no_cache_prompt,
        ctx_size=args.ctx_size,
    )


log = logging.getLogger(__name__)

TOKEN_RESERVE = 520  # 512 for gen + 8 for formatting etc
BATCH_SIZE = 20

GenerationResult = namedtuple("GenerationResult", "success content extra")


class Runner:
    def __init__(
        self,
        bench_setting: str,
        model_name: str = None,
        n_questions: int = None,
        ignore_config=False,
        no_cache_prompt=False,
        ctx_size: int = None,
    ):
        if ctx_size is not None:
            model_key = model_name
            model_name = f"{model_name}-ctx-{ctx_size}"
        else:
            model_key = model_name
        self.bench_setting = bench_setting
        self.model_name = model_name
        self.n_questions = n_questions
        self.ignore_config = ignore_config
        self.no_cache_prompt = no_cache_prompt
        self.prompts = []
        self.engine = get_engine(model_key, ctx_size=ctx_size)
        self.questions = []
        self.write_lock = asyncio.Lock()
        self.results_file = open(REPO_ROOT / f"results/results-{self.bench_setting}-{self.model_name}.jsonl", "a")
        self.extras_file = open(REPO_ROOT / f"results/extra-{self.bench_setting}-{self.model_name}.jsonl", "a")

    def get_questions(self):
        qs = load_questions()

        # filter to only ids in questions
        if not self.ignore_config:
            cfg_fp = REPO_ROOT / f"config/{self.bench_setting}-{self.model_name}.txt"
            if cfg_fp.exists():
                with open(cfg_fp) as f:
                    ids = set(l.strip() for l in f if l.strip())
                qs = [q for q in qs if q["id"] in ids]

        if self.n_questions:
            return qs[: self.n_questions]
        return qs

    def load(self, *args, **kwargs):
        self.questions = self.get_questions()
        self.prompts = self.get_prompts(self.questions)

    def get_prompt(self, question, *args, **kwargs) -> str:
        raise NotImplementedError

    def get_prompts(self, questions, *args, **kwargs) -> list[str]:
        # load existing prompts
        prompt_fp = REPO_ROOT / f"results/prompts-{self.bench_setting}-{self.model_name}.json"
        existing_prompts = {}  # id to prompt
        if prompt_fp.exists() and not self.no_cache_prompt:
            with open(prompt_fp) as f:
                prompts = json.load(f)
            existing_prompts = {p["id"]: p["prompt"] for p in prompts}

        # gen prompts that are missing
        out = []
        for q in tqdm.tqdm(questions):
            if q["id"] in existing_prompts:
                prompt = existing_prompts[q["id"]]
            else:
                prompt = self.get_prompt(q, *args, **kwargs)
                existing_prompts[q["id"]] = prompt
            out.append(prompt)

        # save prompts, merge with existing
        with open(prompt_fp, "w") as f:
            data = [{"id": p_id, "prompt": p} for p_id, p in existing_prompts.items()]
            json.dump(data, f)

        return out

    # def save(self, results: list[GenerationResult]):
    #     output = []
    #     for idx, gen in enumerate(results):
    #         q = self.questions[idx]
    #         data = {"id": q["id"], "answer": gen.content, "question": q, "prompt": self.prompts[idx]}
    #         if gen.extra:
    #             data["extra"] = gen.extra
    #         output.append(data)
    #
    #     with open(REPO_ROOT / f"results/{self.bench_setting}-{self.model_name}.json", "w") as f:
    #         json.dump(output, f, indent=2)

    def save_one(self, result: GenerationResult, idx: int):
        q = self.questions[idx]
        data = {"id": q["id"], "answer": result.content, "question": q}
        self.results_file.write(json.dumps(data))
        self.results_file.write("\n")
        # extras
        data = {
            "id": q["id"],
            "answer": result.content,
            "question": q,
            "prompt": self.prompts[idx],
            "extra": result.extra,
        }
        self.extras_file.write(json.dumps(data))
        self.extras_file.write("\n")

    # runners
    async def run_one(self, prompt, question, kani_cls=Kani, **kwargs) -> GenerationResult:
        ai = kani_cls(self.engine, **kwargs)
        try:
            resp = await ai.chat_round_str(prompt)
            return GenerationResult(success=True, content=resp, extra=None)
        except Exception:
            log.exception("Error getting response")
            return GenerationResult(success=False, content=None, extra=None)

    async def _run_one(self, *args, idx: int, **kwargs):
        result = await self.run_one(*args, **kwargs)
        async with self.write_lock:
            self.save_one(result, idx)
        return result

    async def _run_series(self, *args, **kwargs):
        results = []
        for idx, prompt in tqdm.tqdm(enumerate(self.prompts), total=len(self.prompts)):
            question = self.questions[idx]
            result = await self._run_one(prompt, question, *args, idx=idx, **kwargs)
            results.append(result)
        return results

    async def _run_parallel(self, *args, **kwargs):
        results = []
        for batch in tqdm.tqdm(batched(enumerate(self.prompts), BATCH_SIZE), total=len(self.prompts) // BATCH_SIZE + 1):
            r = await asyncio.gather(
                *(self._run_one(prompt, self.questions[idx], *args, idx=idx, **kwargs) for idx, prompt in batch)
            )
            results.extend(r)
        return results

    async def run(self, kani_cls=Kani, **kwargs) -> list[GenerationResult]:
        if can_parallel(self.engine):
            return await self._run_parallel(kani_cls=kani_cls, **kwargs)
        return await self._run_series(kani_cls=kani_cls, **kwargs)

    async def close(self):
        await self.engine.close()
        self.results_file.close()
        self.extras_file.close()
