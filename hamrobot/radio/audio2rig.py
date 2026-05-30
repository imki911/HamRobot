from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from hamrobot.audio.device import resolve_device
from hamrobot.config import AudioConfig, RadioConfig
from hamrobot.radio.ptt import BasePTT, NullPTT, SerialPTT
from hamrobot.utils.audio import add_silence, duration_seconds, normalize_mono_int16, read_wav

logger = logging.getLogger(__name__)


class Audio2RigRadio:
    def __init__(self, audio_cfg: AudioConfig, radio_cfg: RadioConfig, dry_run: bool = False):
        self.audio_cfg = audio_cfg
        self.radio_cfg = radio_cfg
        self.sample_rate = int(audio_cfg.sample_rate)
        self.output_device = resolve_device(audio_cfg.output_device, "output")
        self.dry_run = dry_run or radio_cfg.mode == "dry-run"
        self.ptt: BasePTT = self._build_ptt()
        self.tx_active = False

    def _build_ptt(self) -> BasePTT:
        if self.radio_cfg.mode == "serial" and self.radio_cfg.ptt_port:
            return SerialPTT(
                port=self.radio_cfg.ptt_port,
                baudrate=self.radio_cfg.ptt_baudrate,
                line=self.radio_cfg.ptt_line,
                active_high=self.radio_cfg.ptt_active_high,
            )
        return NullPTT()

    def close(self) -> None:
        self.ptt.close()

    def transmit_wav(self, wav_path: str | Path) -> None:
        audio, sr = read_wav(wav_path)
        if sr != self.sample_rate:
            raise ValueError(f"TTS sample rate {sr} does not match configured {self.sample_rate}")
        self.transmit_audio(audio)

    def transmit_audio(self, audio: np.ndarray) -> None:
        samples = normalize_mono_int16(audio)
        seconds = duration_seconds(samples, self.sample_rate)
        if seconds > float(self.radio_cfg.max_tx_seconds):
            raise ValueError(f"tx audio too long: {seconds:.1f}s")

        mode = self.radio_cfg.mode.lower()
        if mode == "vox":
            samples = add_silence(
                samples,
                self.sample_rate,
                head_ms=self.radio_cfg.vox_head_silence_ms,
                tail_ms=self.radio_cfg.vox_tail_silence_ms,
            )
            self._play(samples)
            return

        if mode == "serial":
            self.tx_active = True
            try:
                self.ptt.on()
                time.sleep(self.radio_cfg.ptt_pre_delay_ms / 1000.0)
                self._play(samples)
                time.sleep(self.radio_cfg.ptt_post_delay_ms / 1000.0)
            finally:
                self.ptt.off()
                self.tx_active = False
            return

        if mode == "dry-run" or self.dry_run:
            logger.info("dry-run TX skipped duration=%.2fs", seconds)
            return

        raise ValueError(f"unsupported radio mode: {self.radio_cfg.mode}")

    def _play(self, audio: np.ndarray) -> None:
        seconds = duration_seconds(audio, self.sample_rate)
        if self.dry_run:
            logger.info("dry-run playback skipped duration=%.2fs", seconds)
            return
        logger.info("play TX audio duration=%.2fs", seconds)
        data = normalize_mono_int16(audio)
        sd.play(data, samplerate=self.sample_rate, device=self.output_device, blocking=True)
