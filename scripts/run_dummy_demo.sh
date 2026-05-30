#!/usr/bin/env bash
set -euo pipefail
python -m hamrobot.cli -c config/config.example.yaml --dry-run
