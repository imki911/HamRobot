from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def rms_int16(frame: np.ndarray) -> float:
    arr = frame.astype(np.float32).reshape(-1)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(arr * arr)))


def normalize_mono_int16(audio: np.ndarray) -> np.ndarray:
    arr = np.asarray(audio)
    if arr.ndim == 2:
        arr = arr[:, 0]
    if arr.dtype != np.int16:
        if np.issubdtype(arr.dtype, np.floating):
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767).astype(np.int16)
        else:
            arr = arr.astype(np.int16)
    return arr.reshape(-1)


def add_silence(audio: np.ndarray, sample_rate: int, head_ms: int = 0, tail_ms: int = 0) -> np.ndarray:
    arr = normalize_mono_int16(audio)
    head = np.zeros(int(sample_rate * head_ms / 1000), dtype=np.int16)
    tail = np.zeros(int(sample_rate * tail_ms / 1000), dtype=np.int16)
    return np.concatenate([head, arr, tail])


def duration_seconds(audio: np.ndarray, sample_rate: int) -> float:
    return len(normalize_mono_int16(audio)) / float(sample_rate)


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), normalize_mono_int16(audio), sample_rate, subtype="PCM_16")
    return path


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="int16", always_2d=False)
    return normalize_mono_int16(data), int(sr)


def tone(frequency_hz: int, seconds: float, sample_rate: int, amplitude: float = 0.25) -> np.ndarray:
    count = int(sample_rate * seconds)
    t = np.arange(count, dtype=np.float32) / sample_rate
    data = np.sin(2 * np.pi * frequency_hz * t) * amplitude
    return (data * 32767).astype(np.int16)
