from __future__ import annotations

import os
from openai import OpenAI
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
        self.api_key = cfg.api_key_env
        if not self.api_key:
            raise RuntimeError(f"missing environment variable: {cfg.api_key_env}")
        self.endpoint = cfg.base_url.rstrip("/") + "/chat/completions"
        self.client = OpenAI(
            api_key=cfg.api_key_env,
            base_url=cfg.base_url.rstrip("/"),
        )

    def chat(self, user_text: str, history: list[ChatTurn] | None = None) -> str:
        messages = [{"role": "system", "content": self.cfg.system_prompt}]
        if history:
            messages.extend({"role": t.role, "content": t.content} for t in history)
        messages.append({"role": "user", "content": user_text})
        completion = self.client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            # 通过 extra_body 设置 enable_thinking 开启思考模式
            extra_body={"enable_thinking": False},
            stream=True,
            stream_options={
                "include_usage": False
            },
        )
        answer_content = ""  # 完整回复
        for chunk in completion:
            if not chunk.choices:
                print("\n" + "=" * 20 + "Token 消耗" + "=" * 20 + "\n")
                print(chunk.usage)
                continue

            delta = chunk.choices[0].delta
            # 收到content，开始进行回复
            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)
                answer_content += delta.content
        return answer_content


def build_llm(cfg: LLMConfig) -> BaseLLM:
    provider = cfg.provider.lower()
    if provider == "dummy":
        return DummyLLM(cfg.dummy_reply)
    if provider == "deepseek":
        return DeepSeekLLM(cfg)
    raise ValueError(f"unsupported llm provider: {cfg.provider}")
