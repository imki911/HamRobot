from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(level: str = "INFO", file: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if file:
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
