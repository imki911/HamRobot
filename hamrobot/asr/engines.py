from __future__ import annotations

import os
from pathlib import Path

import requests

from hamrobot.asr.base import ASRResult, BaseASR
from hamrobot.config import ASRConfig


class DummyASR(BaseASR):
    def __init__(self, text: str):
        self.text = text

    def transcribe(self, wav_path: Path) -> ASRResult:
        return ASRResult(text=self.text, confidence=1.0, language="zh")


class WhisperASR(BaseASR):
    def __init__(self, cfg: ASRConfig):
        import whisper

        self.cfg = cfg
        self.model = whisper.load_model(cfg.whisper_model)

    def transcribe(self, wav_path: Path) -> ASRResult:
        kwargs = {}
        if self.cfg.language:
            kwargs["language"] = self.cfg.language
            kwargs["initial_prompt"] = (
                "以下是业余无线电通联语音，可能包含中文、英文、数字、呼号、CQ、DE、OVER、Roger。"
            )
        result = self.model.transcribe(str(wav_path), **kwargs)
        return ASRResult(
            text=str(result.get("text", "")).strip(),
            confidence=1.0,
            language=result.get("language"),
        )


class HttpASR(BaseASR):
    def __init__(self, cfg: ASRConfig):
        if not cfg.http_url:
            raise ValueError("asr.http_url is required for http ASR")
        self.cfg = cfg

    def transcribe(self, wav_path: Path) -> ASRResult:
        headers = {}
        key = os.getenv(self.cfg.http_api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        with wav_path.open("rb") as f:
            resp = requests.post(
                self.cfg.http_url,
                files={"file": (wav_path.name, f, "audio/wav")},
                headers=headers,
                timeout=self.cfg.timeout_seconds,
            )
        resp.raise_for_status()
        data = resp.json()
        return ASRResult(
            text=str(data.get("text", "")).strip(),
            confidence=float(data.get("confidence", 1.0)),
            language=data.get("language"),
        )


def build_asr(cfg: ASRConfig) -> BaseASR:
    engine = cfg.engine.lower()
    if engine == "dummy":
        return DummyASR(cfg.dummy_text)
    if engine == "whisper":
        return WhisperASR(cfg)
    if engine == "http":
        return HttpASR(cfg)
    raise ValueError(f"unsupported ASR engine: {cfg.engine}")
