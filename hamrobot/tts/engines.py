from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import requests

from hamrobot.config import TTSConfig
from hamrobot.tts.base import BaseTTS
from hamrobot.utils.audio import tone, write_wav

class DummyTTS(BaseTTS):
    def __init__(self, cfg: TTSConfig, sample_rate: int):
        self.cfg = cfg
        self.sample_rate = sample_rate
        self.output_dir = Path(cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> Path:
        audio = tone(self.cfg.dummy_frequency_hz, self.cfg.dummy_seconds, self.sample_rate)
        return write_wav(self.output_dir / _name(), audio, self.sample_rate)


class Pyttsx3TTS(BaseTTS):
    def __init__(self, cfg: TTSConfig, sample_rate: int):
        self.cfg = cfg
        self.sample_rate = sample_rate
        self.output_dir = Path(cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> Path:
        import pyttsx3

        raw = self.output_dir / _name(prefix="tts_raw", suffix=".wav")
        out = self.output_dir / _name()
        engine = pyttsx3.init()
        engine.setProperty("rate", self.cfg.rate)
        engine.setProperty("volume", self.cfg.volume)
        engine.save_to_file(text, str(raw))
        engine.runAndWait()
        _convert_wav(raw, out, self.sample_rate, self.cfg.ffmpeg_path)
        return out


class EdgeTTS(BaseTTS):
    def __init__(self, cfg: TTSConfig, sample_rate: int):
        self.cfg = cfg
        self.sample_rate = sample_rate
        self.output_dir = Path(cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> Path:
        mp3_path = self.output_dir / _name(prefix="edge", suffix=".mp3")
        wav_path = self.output_dir / _name(prefix="edge", suffix=".wav")
        asyncio.run(self._run_edge(text, mp3_path))
        _convert_wav(mp3_path, wav_path, self.sample_rate, self.cfg.ffmpeg_path)
        return wav_path

    async def _run_edge(self, text: str, mp3_path: Path) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.cfg.edge_voice,
            rate=self.cfg.edge_rate,
            volume=self.cfg.edge_volume,
        )
        await communicate.save(str(mp3_path),)


class HttpTTS(BaseTTS):
    def __init__(self, cfg: TTSConfig, sample_rate: int):
        if not cfg.http_url:
            raise ValueError("tts.http_url is required for http TTS")
        self.cfg = cfg
        self.sample_rate = sample_rate
        self.output_dir = Path(cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> Path:
        headers = {"Content-Type": "application/json"}
        key = os.getenv(self.cfg.http_api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resp = requests.post(
            self.cfg.http_url,
            headers=headers,
            json={"text": text, "sample_rate": self.sample_rate},
            timeout=self.cfg.timeout_seconds,
        )
        resp.raise_for_status()
        out = self.output_dir / _name()
        ctype = resp.headers.get("content-type", "")
        if "audio" in ctype or resp.content[:4] == b"RIFF":
            out.write_bytes(resp.content)
            return out
        data = resp.json()
        pcm = np.asarray(data.get("pcm16", []), dtype=np.int16)
        return write_wav(out, pcm, self.sample_rate)


def build_tts(cfg: TTSConfig, sample_rate: int) -> BaseTTS:
    engine = cfg.engine.lower()
    if engine == "dummy":
        return DummyTTS(cfg, sample_rate)
    if engine == "pyttsx3":
        return Pyttsx3TTS(cfg, sample_rate)
    if engine == "edge":
        return EdgeTTS(cfg, sample_rate)
    if engine == "http":
        return HttpTTS(cfg, sample_rate)
    raise ValueError(f"unsupported TTS engine: {cfg.engine}")


def _name(prefix: str = "tts", suffix: str = ".wav") -> str:
    return f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000:03d}{suffix}"


def _convert_wav(src: Path, dst: Path, sample_rate: int, ffmpeg_path: str) -> None:
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for this TTS output conversion") from exc
