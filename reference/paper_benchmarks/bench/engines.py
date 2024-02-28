import os

import aiolimiter
import torch
from kani import AIFunction, ChatMessage
from kani.engines.anthropic import AnthropicEngine
from kani.engines.base import BaseEngine
from kani.engines.huggingface.llama2 import LlamaEngine
from kani.engines.openai import OpenAIEngine
from kani.engines.openai.models import ChatCompletion

# hf
common_hf_model_args = dict(
    device_map="auto",
    torch_dtype=torch.float16,
)

if mcd := os.getenv("MODEL_CACHE_DIR"):
    common_hf_model_args["cache_dir"] = mcd


def can_parallel(engine):
    return isinstance(engine, OpenAIEngine)


def get_engine(name: str, ctx_size=None) -> BaseEngine:
    if name == "gpt-4":
        return RatelimitedOpenAIEngine(
            model="gpt-4-0613",
            max_context_size=ctx_size or 8192,
            tpm_limiter=aiolimiter.AsyncLimiter(300000),
            temperature=0,
        )
    elif name == "gpt-4-turbo":
        return RatelimitedOpenAIEngine(
            model="gpt-4-0125-preview",
            max_context_size=ctx_size or 128000,
            tpm_limiter=aiolimiter.AsyncLimiter(400000),
            temperature=0,
        )
    elif name == "gpt-3.5-turbo":
        return RatelimitedOpenAIEngine(
            model="gpt-3.5-turbo-1106",
            max_context_size=ctx_size or 16000,
            tpm_limiter=aiolimiter.AsyncLimiter(2000000),
            temperature=0,
        )
    elif name == "llama-chat":
        return LlamaEngine(
            "meta-llama/Llama-2-70b-chat-hf",
            max_context_size=ctx_size or 4096,
            model_load_kwargs=common_hf_model_args,
            use_auth_token=True,
            do_sample=False,
        )
    elif name == "mistral-chat":
        return LlamaEngine(
            "mistralai/Mistral-7B-Instruct-v0.2",
            max_context_size=ctx_size or 32768,
            model_load_kwargs=common_hf_model_args,
            do_sample=False,
        )
    elif name == "mixtral":
        return LlamaEngine(
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_context_size=ctx_size or 32768,
            model_load_kwargs=common_hf_model_args,
            do_sample=False,
        )
    elif name == "longllama":
        return LlamaEngine(
            "syzymon/long_llama_3b_instruct",
            max_context_size=ctx_size or 512000,
            tokenizer_kwargs={"trust_remote_code": True},
            model_load_kwargs={"trust_remote_code": True, **common_hf_model_args},
            do_sample=False,
        )
    elif name == "claude":
        return AnthropicEngine(
            model="claude-2.1",
            max_context_size=ctx_size or 200000,
            temperature=0,
        )
    else:
        raise ValueError("Invalid model name")


class RatelimitedOpenAIEngine(OpenAIEngine):
    def __init__(
        self, *args, rpm_limiter: aiolimiter.AsyncLimiter = None, tpm_limiter: aiolimiter.AsyncLimiter = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.rpm_limiter = rpm_limiter
        self.tpm_limiter = tpm_limiter

    async def predict(
        self, messages: list[ChatMessage], functions: list[AIFunction] | None = None, **hyperparams
    ) -> ChatCompletion:
        if self.rpm_limiter:
            await self.rpm_limiter.acquire()
        if self.tpm_limiter:
            n_toks = self.function_token_reserve(functions) + sum(self.message_len(m) for m in messages)
            await self.tpm_limiter.acquire(n_toks)
        return await super().predict(messages, functions, **hyperparams)
