from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatTurn:
    role: str
    content: str


class BaseLLM:
    def chat(self, user_text: str, history: list[ChatTurn] | None = None) -> str:
        raise NotImplementedError
