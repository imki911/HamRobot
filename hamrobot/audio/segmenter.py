from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd

from hamrobot.config import AudioConfig, SegmenterConfig
from hamrobot.audio.device import resolve_device
from hamrobot.utils.audio import rms_int16, write_wav

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    samples: np.ndarray
    sample_rate: int
    wav_path: Path | None
    started_at: float
    ended_at: float
    peak_rms: float


class EnergySegmenter:
    def __init__(self, audio_cfg: AudioConfig, seg_cfg: SegmenterConfig):
        self.audio_cfg = audio_cfg
        self.seg_cfg = seg_cfg
        self.sample_rate = int(audio_cfg.sample_rate)
        self.block_size = int(self.sample_rate * audio_cfg.block_ms / 1000)
        self.input_device = resolve_device(audio_cfg.input_device, "input")
        self.save_dir = Path(audio_cfg.save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = float(seg_cfg.min_threshold)

    def _read_block(self, stream: sd.InputStream) -> np.ndarray:
        data, overflowed = stream.read(self.block_size)
        if overflowed:
            logger.warning("audio input overflow")
        arr = np.asarray(data)
        if arr.ndim == 2:
            arr = arr[:, 0]
        return arr.astype(np.int16, copy=False)

    def calibrate(self) -> None:
        blocks = max(1, int(self.seg_cfg.calibrate_seconds * 1000 / self.audio_cfg.block_ms))
        values: list[float] = []
        with sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.audio_cfg.channels,
            dtype=self.audio_cfg.dtype,
            device=self.input_device,
        ) as stream:
            for _ in range(blocks):
                values.append(rms_int16(self._read_block(stream)))
        noise = float(np.median(values)) if values else 0.0
        self.threshold = max(float(self.seg_cfg.min_threshold), noise * float(self.seg_cfg.threshold_ratio))
        logger.info("calibrated noise_rms=%.1f threshold=%.1f", noise, self.threshold)

    def wait_for_segment(self, stop_event: threading.Event | None = None) -> AudioSegment | None:
        start_frames = max(1, int(self.seg_cfg.start_voice_ms / self.audio_cfg.block_ms))
        silence_frames = max(1, int(self.seg_cfg.end_silence_ms / self.audio_cfg.block_ms))
        min_frames = max(1, int(self.seg_cfg.min_record_ms / self.audio_cfg.block_ms))
        max_frames = max(1, int(self.seg_cfg.max_record_seconds * 1000 / self.audio_cfg.block_ms))
        pre_frames = max(0, int(self.seg_cfg.pre_roll_ms / self.audio_cfg.block_ms))
        pre_roll: deque[np.ndarray] = deque(maxlen=pre_frames)
        voice_count = 0
        silence_count = 0
        recording = False
        recorded: list[np.ndarray] = []
        started = ended = 0.0
        peak_rms = 0.0

        with sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.audio_cfg.channels,
            dtype=self.audio_cfg.dtype,
            device=self.input_device,
        ) as stream:
            while True:
                if stop_event is not None and stop_event.is_set():
                    logger.info("segment wait stopped")
                    return None

                frame = self._read_block(stream)

                if stop_event is not None and stop_event.is_set():
                    logger.info("segment wait stopped after read")
                    return None

                value = rms_int16(frame)
                peak_rms = max(peak_rms, value)
                is_voice = value >= self.threshold
                if not recording:
                    pre_roll.append(frame.copy())
                    voice_count = voice_count + 1 if is_voice else 0
                    if voice_count >= start_frames:
                        recording = True
                        started = time.time()
                        recorded.extend([x.copy() for x in pre_roll])
                        recorded.append(frame.copy())
                        silence_count = 0
                        logger.info("segment started rms=%.1f", value)
                    continue

                recorded.append(frame.copy())
                if is_voice:
                    silence_count = 0
                else:
                    silence_count += 1

                if silence_count >= silence_frames or len(recorded) >= max_frames:
                    ended = time.time()
                    break

        if len(recorded) < min_frames:
            logger.info("drop short segment frames=%d", len(recorded))
            return None
        samples = np.concatenate(recorded).astype(np.int16, copy=False)
        name = time.strftime("rx_%Y%m%d_%H%M%S.wav", time.localtime(started))
        wav_path = write_wav(self.save_dir / name, samples, self.sample_rate)
        logger.info("segment saved %s duration=%.2fs", wav_path, len(samples) / self.sample_rate)
        return AudioSegment(samples, self.sample_rate, wav_path, started, ended, peak_rms)
