from __future__ import annotations

import os

import requests

from hamrobot.config import LLMConfig
from hamrobot.llm.base import BaseLLM, ChatTurn


class DummyLLM(BaseLLM):
    def __init__(self, reply: str):
        self.reply = reply

    def chat(self, user_text: str, history: list[ChatTurn] | None = None) -> str:
        return self.reply


class DeepSeekLLM(BaseLLM):
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.api_key = os.getenv(cfg.api_key_env, "")
        if not self.api_key:
            raise RuntimeError(f"missing environment variable: {cfg.api_key_env}")
        self.endpoint = cfg.base_url.rstrip("/") + "/chat/completions"

    def chat(self, user_text: str, history: list[ChatTurn] | None = None) -> str:
        messages = [{"role": "system", "content": self.cfg.system_prompt}]
        if history:
            messages.extend({"role": t.role, "content": t.content} for t in history)
        messages.append({"role": "user", "content": user_text})
        resp = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.cfg.model,
                "messages": messages,
                "temperature": self.cfg.temperature,
                "max_tokens": self.cfg.max_tokens,
            },
            timeout=self.cfg.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()


def build_llm(cfg: LLMConfig) -> BaseLLM:
    provider = cfg.provider.lower()
    if provider == "dummy":
        return DummyLLM(cfg.dummy_reply)
    if provider == "deepseek":
        return DeepSeekLLM(cfg)
    raise ValueError(f"unsupported llm provider: {cfg.provider}")
