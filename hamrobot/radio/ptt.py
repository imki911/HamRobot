from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class BasePTT:
    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class NullPTT(BasePTT):
    def on(self) -> None:
        logger.debug("PTT ON skipped")

    def off(self) -> None:
        logger.debug("PTT OFF skipped")

    def close(self) -> None:
        return None


@dataclass
class SerialPTT(BasePTT):
    port: str
    baudrate: int = 9600
    line: str = "rts"
    active_high: bool = True

    def __post_init__(self) -> None:
        import serial

        self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        self.off()

    def _set(self, active: bool) -> None:
        value = bool(active) if self.active_high else not bool(active)
        line = self.line.lower()
        if line == "rts":
            self._serial.rts = value
        elif line == "dtr":
            self._serial.dtr = value
        else:
            raise ValueError("ptt line must be 'rts' or 'dtr'")

    def on(self) -> None:
        logger.info("PTT ON")
        self._set(True)

    def off(self) -> None:
        logger.info("PTT OFF")
        self._set(False)

    def close(self) -> None:
        self.off()
        self._serial.close()
