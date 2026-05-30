from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from hamrobot.config import DialogConfig
from hamrobot.llm.base import ChatTurn


@dataclass
class DialogDecision:
    should_reply: bool
    reason: str = ""
    normalized_text: str = ""


@dataclass
class DialogManager:
    cfg: DialogConfig
    history: list[ChatTurn] = field(default_factory=list)
    last_tx_at: float = 0.0

    def decide(self, text: str) -> DialogDecision:
        normalized = self._normalize(text)
        if not normalized:
            return DialogDecision(False, "empty", normalized)
        elapsed = time.time() - self.last_tx_at
        if elapsed < self.cfg.tx_cooldown_seconds:
            return DialogDecision(False, "cooldown", normalized)
        if self.cfg.require_wake_word and not self._has_wake_word(normalized):
            return DialogDecision(False, "wake_word_missing", normalized)
        return DialogDecision(True, "ok", normalized)

    def mark_tx(self) -> None:
        self.last_tx_at = time.time()

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self.history.append(ChatTurn("user", user_text))
        self.history.append(ChatTurn("assistant", assistant_text))
        max_items = max(0, self.cfg.max_history_turns * 2)
        if max_items:
            self.history = self.history[-max_items:]

    def trim_reply(self, text: str) -> str:
        text = self._normalize(text)
        text = re.sub(r"[`*_#>\[\]{}|]", "", text)
        if len(text) <= self.cfg.max_reply_chars:
            return text
        return text[: self.cfg.max_reply_chars].rstrip("，。；、 ") + "。"

    def _has_wake_word(self, text: str) -> bool:
        return any(w and w in text for w in self.cfg.wake_words)

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", "", text or "").strip()
