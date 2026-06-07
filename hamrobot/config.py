from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _get(d: dict[str, Any], key: str, default: Any) -> Any:
    value = d.get(key, default)
    return default if value is None else value


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    block_ms: int = 20
    input_device: int | str | None = None
    output_device: int | str | None = None
    save_dir: str = "runtime/recordings"


@dataclass
class SegmenterConfig:
    calibrate_seconds: float = 1.0
    threshold_ratio: float = 3.0
    min_threshold: float = 300.0
    start_voice_ms: int = 300
    end_silence_ms: int = 1000
    min_record_ms: int = 500
    max_record_seconds: float = 12
    pre_roll_ms: int = 300


@dataclass
class ASRConfig:
    engine: str = "whisper"
    whisper_model: str = "base"
    language: str | None = "zh"
    http_url: str = ""
    http_api_key_env: str = "ASR_API_KEY"
    timeout_seconds: int = 60
    dummy_text: str = "机器人，收到请回答"
    min_confidence: float = 0.3

    # DashScope fun-asr-realtime local-file mode.
    # The key is intentionally read from config as requested by the project owner.
    dashscope_api_key: str = ""
    dashscope_model: str = "fun-asr-realtime"
    dashscope_format: str = "wav"
    dashscope_sample_rate: int = 16000
    dashscope_base_http_api_url: str = "https://dashscope.aliyuncs.com/api/v1"
    dashscope_base_websocket_api_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    # DashScope hotword vocabulary. Each item is like {"text": "BH4HZU", "weight": 4}.
    # Weight usually ranges from 1 to 5. Higher values bias recognition more strongly.
    dashscope_vocabulary_enabled: bool = True
    dashscope_vocabulary_prefix: str = "hamrobot"
    dashscope_vocabulary_delete_after_call: bool = True
    dashscope_vocabulary: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"text": "BH4HZU", "weight": 5},
            {"text": "CQ", "weight": 4},
            {"text": "DE", "weight": 4},
            {"text": "QTH", "weight": 4},
            {"text": "QSL", "weight": 4},
            {"text": "QRZ", "weight": 4},
            {"text": "OVER", "weight": 4},
            {"text": "ROGER", "weight": 4},
            {"text": "73", "weight": 3},
            {"text": "昆山", "weight": 3},
            {"text": "周庄", "weight": 3},
            {"text": "泉盛", "weight": 3},
            {"text": "晾衣杆天线", "weight": 3},
        ]
    )


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com/v1"
    api_key_env: str = "DEEPSEEK_API_KEY"
    model: str = "deepseek-chat"
    timeout_seconds: int = 60
    temperature: float = 0.3
    max_tokens: int = 120
    system_prompt: str = "你是一个HAM（业余无线电玩家），守听线上的呼叫并做出回应。针对收听到的呼叫，"
    dummy_reply: str = "收到，语音链路正常。"


@dataclass
class TTSConfig:
    vox_prefix_ms: int = 500
    engine: str = "pyttsx3"
    output_dir: str = "runtime/tts"
    rate: int = 170
    volume: float = 1.0
    edge_voice: str = "zh-CN-XiaoxiaoNeural"
    edge_rate: str = "-10%"
    edge_volume: str = "+0%"
    ffmpeg_path: str = "ffmpeg"
    http_url: str = ""
    http_api_key_env: str = "TTS_API_KEY"
    timeout_seconds: int = 60
    dummy_frequency_hz: int = 880
    dummy_seconds: float = 1.2


@dataclass
class DialogConfig:
    require_wake_word: bool = True
    wake_words: list[str] = field(default_factory=lambda: ["机器人", "小智", "调度台"])
    max_reply_chars: int = 80
    tx_cooldown_seconds: float = 3
    max_history_turns: int = 4


@dataclass
class RadioConfig:
    mode: str = "vox"
    ptt_port: str | None = None
    ptt_baudrate: int = 9600
    ptt_line: str = "rts"
    ptt_active_high: bool = True
    ptt_pre_delay_ms: int = 250
    ptt_post_delay_ms: int = 400
    vox_head_silence_ms: int = 500
    vox_tail_silence_ms: int = 800
    max_tx_seconds: float = 25


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "runtime/hamrobot.log"


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    segmenter: SegmenterConfig = field(default_factory=SegmenterConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    dialog: DialogConfig = field(default_factory=DialogConfig)
    radio: RadioConfig = field(default_factory=RadioConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def load_config(path: str | Path) -> AppConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return AppConfig(
        audio=AudioConfig(**_section(data, "audio")),
        segmenter=SegmenterConfig(**_section(data, "segmenter")),
        asr=ASRConfig(**_section(data, "asr")),
        llm=LLMConfig(**_section(data, "llm")),
        tts=TTSConfig(**_section(data, "tts")),
        dialog=DialogConfig(**_section(data, "dialog")),
        radio=RadioConfig(**_section(data, "radio")),
        logging=LoggingConfig(**_section(data, "logging")),
    )
