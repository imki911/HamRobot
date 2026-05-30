from __future__ import annotations

from pathlib import Path


class BaseTTS:
    def synthesize(self, text: str) -> Path:
        raise NotImplementedError
