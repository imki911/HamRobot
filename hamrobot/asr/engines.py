from __future__ import annotations

import logging
import os
from http import HTTPStatus
from pathlib import Path
from typing import Any

import requests

from hamrobot.asr.base import ASRResult, BaseASR
from hamrobot.config import ASRConfig

logger = logging.getLogger(__name__)


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


class DashScopeRealtimeFileASR(BaseASR):
    """DashScope fun-asr-realtime wrapper that accepts a local wav file path.

    This uses the official dashscope SDK Recognition.call(local_file) style. It keeps
    HamRobot's current batch-ASR state machine unchanged while replacing slow local
    Whisper inference with a remote realtime model call.
    """

    def __init__(self, cfg: ASRConfig):
        import dashscope
        from dashscope.audio.asr import Recognition

        self.cfg = cfg
        self.Recognition = Recognition
        api_key = (cfg.dashscope_api_key or "").strip()
        if not api_key or api_key == "YOUR_DASHSCOPE_API_KEY":
            raise RuntimeError("asr.dashscope_api_key is required for dashscope_realtime_file")
        dashscope.api_key = api_key
        if cfg.dashscope_base_websocket_api_url:
            dashscope.base_websocket_api_url = cfg.dashscope_base_websocket_api_url

    def transcribe(self, wav_path: Path) -> ASRResult:
        wav_path = Path(wav_path)
        if not wav_path.exists():
            raise FileNotFoundError(wav_path)

        recognition = self.Recognition(
            model=self.cfg.dashscope_model,
            format=self.cfg.dashscope_format,
            sample_rate=self.cfg.dashscope_sample_rate,
            callback=None,
        )
        result = recognition.call(str(wav_path))
        if result.status_code != HTTPStatus.OK:
            message = getattr(result, "message", "") or str(result)
            raise RuntimeError(f"DashScope ASR failed: {message}")

        text = self._extract_sentence(result)
        self._log_metrics(recognition)
        return ASRResult(text=text, confidence=1.0, language=self.cfg.language)

    @staticmethod
    def _extract_sentence(result: Any) -> str:
        sentence = result.get_sentence() if hasattr(result, "get_sentence") else ""
        return DashScopeRealtimeFileASR._sentence_to_text(sentence).strip()

    @staticmethod
    def _sentence_to_text(sentence: Any) -> str:
        if sentence is None:
            return ""
        if isinstance(sentence, str):
            return sentence
        if isinstance(sentence, dict):
            for key in ("text", "sentence", "transcript"):
                value = sentence.get(key)
                if value:
                    return DashScopeRealtimeFileASR._sentence_to_text(value)
            for key in ("sentences", "results"):
                value = sentence.get(key)
                if value:
                    return DashScopeRealtimeFileASR._sentence_to_text(value)
            return ""
        if isinstance(sentence, list):
            return "".join(DashScopeRealtimeFileASR._sentence_to_text(item) for item in sentence)
        return str(sentence)

    @staticmethod
    def _log_metrics(recognition: Any) -> None:
        try:
            logger.info(
                "DashScope ASR request_id=%s first_package_delay_ms=%s last_package_delay_ms=%s",
                recognition.get_last_request_id(),
                recognition.get_first_package_delay(),
                recognition.get_last_package_delay(),
            )
        except Exception:
            logger.debug("DashScope ASR metrics unavailable", exc_info=True)


def build_asr(cfg: ASRConfig) -> BaseASR:
    engine = cfg.engine.lower()
    if engine == "dummy":
        return DummyASR(cfg.dummy_text)
    if engine == "whisper":
        return WhisperASR(cfg)
    if engine == "http":
        return HttpASR(cfg)
    if engine in {"dashscope_realtime_file", "dashscope_fun_asr", "fun_asr_realtime", "fun-asr-realtime"}:
        return DashScopeRealtimeFileASR(cfg)
    raise ValueError(f"unsupported ASR engine: {cfg.engine}")
