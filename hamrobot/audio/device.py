from __future__ import annotations

from typing import Any

import sounddevice as sd


def list_devices() -> str:
    devices = sd.query_devices()
    rows: list[str] = []
    for i, dev in enumerate(devices):
        rows.append(
            f"[{i:02d}] {dev['name']} | in={dev['max_input_channels']} "
            f"out={dev['max_output_channels']} default_sr={int(dev['default_samplerate'])}"
        )
    return "\n".join(rows)


def resolve_device(selector: int | str | None, kind: str) -> int | None:
    if selector is None:
        return None
    if isinstance(selector, int):
        return selector
    text = str(selector).strip().lower()
    if text == "":
        return None
    devices = sd.query_devices()
    matches: list[int] = []
    for i, dev in enumerate(devices):
        channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
        if channels > 0 and text in dev["name"].lower():
            matches.append(i)
    if not matches:
        raise ValueError(f"No {kind} audio device matches: {selector}")
    return matches[0]


def device_info(index: int | None) -> dict[str, Any] | None:
    if index is None:
        return None
    return dict(sd.query_devices(index))
