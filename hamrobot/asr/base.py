from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ASRResult:
    text: str
    confidence: float = 1.0
    language: str | None = None


class BaseASR:
    def transcribe(self, wav_path: Path) -> ASRResult:
        raise NotImplementedError
