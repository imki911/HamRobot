from __future__ import annotations

import logging
import signal
import threading
from dataclasses import dataclass
from opencc import OpenCC

from hamrobot.asr.engines import build_asr
from hamrobot.audio.segmenter import EnergySegmenter
from hamrobot.config import AppConfig
from hamrobot.dialog.manager import DialogManager
from hamrobot.llm.deepseek import build_llm
from hamrobot.radio.audio2rig import Audio2RigRadio
from hamrobot.tts.engines import build_tts

logger = logging.getLogger(__name__)


@dataclass
class HamRobotApp:
    cfg: AppConfig
    dry_run: bool = False

    def __post_init__(self) -> None:
        if self.dry_run:
            self.cfg.radio.mode = "dry-run"
        self.stop_event = threading.Event()
        self.segmenter = EnergySegmenter(self.cfg.audio, self.cfg.segmenter)
        self.asr = build_asr(self.cfg.asr)
        self.llm = build_llm(self.cfg.llm)
        self.tts = build_tts(self.cfg.tts, self.cfg.audio.sample_rate)
        self.dialog = DialogManager(self.cfg.dialog)
        self.radio = Audio2RigRadio(self.cfg.audio, self.cfg.radio, dry_run=self.dry_run)

    def install_signal_handlers(self) -> None:
        def _stop(signum, frame):  # noqa: ANN001
            logger.info("received signal %s, stopping", signum)
            self.stop_event.set()

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

    def run(self) -> None:
        logger.info("HamRobot started")
        self.segmenter.calibrate()
        while not self.stop_event.is_set():
            if self.radio.tx_active:
                continue
            try:
                segment = self.segmenter.wait_for_segment()
                if segment is None or segment.wav_path is None:
                    continue
                result = self.asr.transcribe(segment.wav_path)
                logger.info("ASR text=%s confidence=%.2f", result.text, result.confidence)
                if result.confidence < self.cfg.asr.min_confidence:
                    logger.info("ASR confidence too low")
                    continue
                cc = OpenCC("t2s")  # Traditional to Simplified
                text = cc.convert(result.text)
                decision = self.dialog.decide(text)
                if not decision.should_reply:
                    logger.info("dialog skipped reason=%s text=%s", decision.reason, decision.normalized_text)
                    continue
                reply = self.llm.chat(decision.normalized_text, self.dialog.history)
                reply = self.dialog.trim_reply(reply)
                if not reply:
                    logger.info("empty LLM reply")
                    continue
                logger.info("reply=%s", reply)
                wav_path = self.tts.synthesize(reply)
                self.radio.transmit_wav(wav_path)
                self.dialog.mark_tx()
                self.dialog.add_turn(decision.normalized_text, reply)
            except Exception:
                logger.exception("main loop error")
        self.radio.close()
        logger.info("HamRobot stopped")
