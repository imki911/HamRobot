from __future__ import annotations

import argparse
import sys

from hamrobot.app import HamRobotApp
from hamrobot.audio.device import list_devices
from hamrobot.config import load_config
from hamrobot.tts.engines import build_tts
from hamrobot.utils.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HamRobot voice assistant")
    parser.add_argument("-c", "--config", default="config/config.example.yaml", help="config yaml path")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("--dry-run", action="store_true", help="run without transmitting audio")
    parser.add_argument("--test-tts", default=None, help="synthesize text and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_devices:
        print(list_devices())
        return 0
    cfg = load_config(args.config)
    setup_logging(cfg.logging.level, cfg.logging.file)
    if args.test_tts is not None:
        tts = build_tts(cfg.tts, cfg.audio.sample_rate)
        path = tts.synthesize(args.test_tts)
        print(path)
        return 0
    app = HamRobotApp(cfg, dry_run=args.dry_run)
    app.install_signal_handlers()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
