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
        # 取第 1 个声道。对讲机场景一般用单声道即可。
        arr = arr[:, 0]

    if arr.dtype != np.int16:
        if np.issubdtype(arr.dtype, np.floating):
            # 假设 float 音频范围是 -1.0 ~ 1.0
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767).astype(np.int16)
        else:
            arr = arr.astype(np.int16)

    return arr.reshape(-1)


def tone(
    frequency_hz: int,
    seconds: float,
    sample_rate: int,
    amplitude: float = 0.25,
    fade_ms: int = 10,
) -> np.ndarray:
    """
    生成 int16 正弦音。

    frequency_hz:
        正弦音频率。VOX 触发建议 800Hz ~ 1200Hz。
    seconds:
        持续时间，单位秒。
    sample_rate:
        采样率。
    amplitude:
        幅度，范围 0.0 ~ 1.0。建议 0.15 ~ 0.3。
    fade_ms:
        淡入淡出时间，避免开头/结尾有爆音。
    """
    count = int(sample_rate * seconds)
    if count <= 0:
        return np.zeros(0, dtype=np.int16)

    amplitude = float(np.clip(amplitude, 0.0, 1.0))

    t = np.arange(count, dtype=np.float32) / sample_rate
    data = np.sin(2 * np.pi * frequency_hz * t) * amplitude

    # 加淡入淡出，避免“啪”一声
    fade_len = int(sample_rate * fade_ms / 1000)
    fade_len = min(fade_len, count // 2)

    if fade_len > 0:
        fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

        data[:fade_len] *= fade_in
        data[-fade_len:] *= fade_out

    data = np.clip(data, -1.0, 1.0)
    return (data * 32767).astype(np.int16)


def silence(seconds: float, sample_rate: int) -> np.ndarray:
    count = int(sample_rate * seconds)
    if count <= 0:
        return np.zeros(0, dtype=np.int16)
    return np.zeros(count, dtype=np.int16)


def add_silence(
    audio: np.ndarray,
    sample_rate: int,
    head_ms: int = 0,
    tail_ms: int = 0,
    *,
    head_as_vox_tone: bool = True,
    vox_tone_frequency_hz: int = 1000,
    vox_tone_amplitude: float = 0.25,
) -> np.ndarray:
    """
    在音频前后追加片段。

    注意：
    - 如果 audio2rig 依靠 VOX 检测音频来触发 PTT，前缀不能用纯静音。
      纯静音是 0 电平，通常不会触发 VOX。
    - 因此默认 head_ms 生成一段正弦音，用于提前触发 VOX/PTT。
    - tail_ms 默认仍然使用静音。尾部通常依靠 audio2rig 的 VOX hang time 维持，
      不建议尾部再加正弦音，否则每次结束都会多一个“滴”声。

    参数：
    audio:
        原始音频。
    sample_rate:
        采样率。
    head_ms:
        前缀时长，单位 ms。VOX 建议 300~600ms。
    tail_ms:
        尾部时长，单位 ms。一般 100~300ms 即可。
    head_as_vox_tone:
        True：head_ms 生成正弦音，用于触发 VOX。
        False：head_ms 生成纯静音。
    vox_tone_frequency_hz:
        VOX 触发音频率。建议 800~1200Hz。
    vox_tone_amplitude:
        VOX 触发音幅度。建议 0.15~0.3。
    """
    arr = normalize_mono_int16(audio)

    head_seconds = head_ms / 1000.0
    tail_seconds = tail_ms / 1000.0

    if head_ms > 0:
        if head_as_vox_tone:
            head = tone(
                frequency_hz=vox_tone_frequency_hz,
                seconds=head_seconds,
                sample_rate=sample_rate,
                amplitude=vox_tone_amplitude,
            )
        else:
            head = silence(head_seconds, sample_rate)
    else:
        head = np.zeros(0, dtype=np.int16)

    if tail_ms > 0:
        tail = silence(tail_seconds, sample_rate)
    else:
        tail = np.zeros(0, dtype=np.int16)

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