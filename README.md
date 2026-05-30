# HamRobot

HamRobot 是一个面向模拟射频对讲机的半双工语音应答机器人。它把 Audio2Rig、USB2Rig、CM108 声卡盒或其他 USB 声卡接口接入上位机，将对讲机收到的语音切句后送入 ASR，再把识别文本交给大语言模型生成短回复，最后通过 TTS 合成语音并经 Audio2Rig 发回对讲机。

项目目标不是替代对讲机的射频部分，而是让现有模拟对讲机继续负责收发射频，上位机负责语音识别、对话和语音合成。

```text
另一台对讲机语音
  ↓
本机对讲机接收
  ↓
Audio2Rig / USB声卡输入
  ↓
HamRobot：VAD切句 → ASR → 唤醒词判断 → DeepSeek LLM → TTS
  ↓
Audio2Rig / USB声卡输出
  ↓
本机对讲机发射
```

## 功能点

- Audio2Rig / USB 声卡输入输出适配
- 音频设备枚举，支持按设备名或设备序号选择输入/输出
- 语音切句：RMS 能量阈值、自动噪声底校准、最短/最长录音保护
- ASR 抽象接口
  - 本地 Whisper
  - HTTP ASR 预留
  - Dummy ASR 测试模式
- LLM 抽象接口
  - DeepSeek OpenAI-compatible `/chat/completions`
  - Dummy LLM 测试模式
- TTS 抽象接口
  - `pyttsx3` 本地 TTS
  - `edge-tts` 可选在线 TTS
  - HTTP TTS 预留
  - Dummy TTS 测试音
- 对讲机发射调度
  - VOX 模式：播放前导/尾部静音，适配 Audio2Rig 自动触发
  - Serial PTT 模式：通过 USB 串口 RTS/DTR 控制 PTT
  - TX mute：发射期间禁止识别自己的语音，避免自我循环
- 唤醒词控制，避免频道里任何语音都触发自动回复
- 回复长度限制，适配无线电窄带语音
- 录音保存和运行日志
- Dry-run 模式，便于无对讲机情况下验证 ASR/LLM/TTS

## 目录结构

```text
HamRobot/
  README.md
  pyproject.toml
  config/
    config.example.yaml       # 示例配置
  hamrobot/
    cli.py                    # 命令行入口
    app.py                    # 主状态机
    config.py                 # YAML配置加载
    audio/
      device.py               # 音频设备枚举/匹配
      segmenter.py            # VAD/能量切句
    radio/
      audio2rig.py            # Audio2Rig输入输出和发射调度
      ptt.py                  # PTT控制，支持RTS/DTR
    asr/
      base.py
      engines.py              # Whisper/HTTP/Dummy ASR
    llm/
      base.py
      deepseek.py             # DeepSeek兼容接口
    tts/
      base.py
      engines.py              # pyttsx3/edge/http/dummy TTS
    dialog/
      manager.py              # 唤醒词、上下文、回复限长
    utils/
      audio.py
      logging.py
  tests/
    test_audio_utils.py
    test_dialog.py
  scripts/
    run_dummy_demo.sh
```

## 硬件连接建议

最小硬件链路：

```text
对讲机 K 头 / 附件口
  ↕
Audio2Rig / USB2Rig / CM108电台接口
  ↕ USB
上位机运行 HamRobot
```

如果 Audio2Rig 使用 VOX：

```text
HamRobot播放TTS音频
  ↓
Audio2Rig/对讲机VOX触发PTT
  ↓
对讲机发射
```

如果需要更稳定的发射时序，建议使用串口 PTT：

```text
USB串口 RTS/DTR → 光耦/三极管 → 对讲机PTT脚对GND短接
```

Serial PTT 模式下 HamRobot 会执行：

```text
PTT ON
等待 ptt_pre_delay_ms
播放 TTS
等待 ptt_post_delay_ms
PTT OFF
```

## 安装

建议 Python 3.10 或更高版本。

```bash
git clone https://github.com/imki911/HamRobot.git
cd HamRobot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

如果使用 Edge TTS：

```bash
pip install -e '.[edge]'
```

Edge TTS 输出 MP3，项目会调用 `ffmpeg` 转成 16kHz mono WAV。需要本机安装 ffmpeg，并保证命令行可访问。

如果使用 Whisper，本地首次运行会下载模型：

```bash
pip install openai-whisper
```

Windows 上还可能需要安装 PyAudio/PortAudio 相关运行库；本项目使用 `sounddevice`，通常比 PyAudio 更省事，但仍依赖系统音频后端。

## 配置

复制示例配置：

```bash
cp config/config.example.yaml config/config.local.yaml
```

列出音频设备：

```bash
python -m hamrobot.cli --list-devices
```

示例输出：

```text
[00] Microsoft Sound Mapper - Input | in=2 out=0 default_sr=44100
[01] USB Audio Device              | in=1 out=2 default_sr=48000
[02] Microsoft Sound Mapper - Output| in=0 out=2 default_sr=44100
```

修改配置中的设备：

```yaml
audio:
  input_device: "USB Audio"
  output_device: "USB Audio"
```

也可以使用序号：

```yaml
audio:
  input_device: 1
  output_device: 1
```

## DeepSeek 配置

配置文件里预留了 DeepSeek 兼容接口：

```yaml
llm:
  provider: deepseek
  base_url: "https://api.deepseek.com/v1"
  api_key_env: DEEPSEEK_API_KEY
  model: deepseek-chat
```

运行前设置环境变量：

```bash
export DEEPSEEK_API_KEY="你的API Key"
# Windows PowerShell:
# $env:DEEPSEEK_API_KEY="你的API Key"
```

如果你使用代理网关或自建兼容接口，修改 `base_url` 即可。最终请求地址为：

```text
{base_url}/chat/completions
```

## 运行

### 1. 先做设备枚举

```bash
python -m hamrobot.cli --list-devices
```

### 2. 测试 TTS

```bash
python -m hamrobot.cli -c config/config.local.yaml --test-tts "收到，语音链路正常。"
```

命令会输出生成的 WAV 文件路径。确认 TTS 能正常生成后，再接入发射链路。

### 3. Dry-run 验证主流程

```bash
python -m hamrobot.cli -c config/config.local.yaml --dry-run
```

Dry-run 会执行录音、ASR、LLM、TTS，但不会向对讲机发射音频。

### 4. 正式运行

```bash
python -m hamrobot.cli -c config/config.local.yaml
```

默认配置要求唤醒词，例如：

```text
机器人，收到请回答
```

系统会生成短回复并通过 Audio2Rig 输出。

## VOX 模式配置

Audio2Rig 原型阶段通常可先用 VOX：

```yaml
radio:
  mode: vox
  vox_head_silence_ms: 500
  vox_tail_silence_ms: 800
```

这会在 TTS 前后加静音，降低开头被 VOX 吃掉的概率。

## 串口 PTT 模式配置

如果你增加了 USB 串口或 USB2Rig 串口 PTT：

```yaml
radio:
  mode: serial
  ptt_port: COM3          # Linux: /dev/ttyUSB0
  ptt_baudrate: 9600
  ptt_line: rts           # rts 或 dtr
  ptt_active_high: true
  ptt_pre_delay_ms: 250
  ptt_post_delay_ms: 400
```

如果 PTT 逻辑相反，把 `ptt_active_high` 改为 `false`。

## ASR 选择

默认使用本地 Whisper：

```yaml
asr:
  engine: whisper
  whisper_model: base
  language: zh
```

测试阶段可用 Dummy ASR：

```yaml
asr:
  engine: dummy
```

HTTP ASR 预留：

```yaml
asr:
  engine: http
  http_url: "https://your-asr-service/transcribe"
  http_api_key_env: ASR_API_KEY
```

HTTP ASR 请求格式：`multipart/form-data`，字段名为 `file`，文件类型为 `audio/wav`。期望返回：

```json
{"text":"机器人收到请回答","confidence":0.95}
```

## TTS 选择

本地 pyttsx3：

```yaml
tts:
  engine: pyttsx3
  rate: 170
  volume: 1.0
```

Edge TTS：

```yaml
tts:
  engine: edge
  edge_voice: zh-CN-XiaoxiaoNeural
  ffmpeg_path: ffmpeg
```

HTTP TTS 预留：

```yaml
tts:
  engine: http
  http_url: "https://your-tts-service/synthesize"
  http_api_key_env: TTS_API_KEY
```

HTTP TTS 可以直接返回 `audio/wav`，或者返回 JSON：

```json
{"pcm16":[0, 13, -20, ...]}
```

## 调试建议

1. 先用录音软件确认 Audio2Rig 输入能收到对讲机音频。
2. 再用系统播放器确认 Audio2Rig 输出能触发 VOX 或进入对讲机 MIC。
3. `--list-devices` 找到正确设备后写入配置。
4. 使用 `--dry-run` 验证 ASR/LLM/TTS。
5. 最后打开真实发射。

## 安全和合规

- 只在你有权使用的频点、功率和设备上测试。
- 不要让系统对频道内所有声音自动回复，建议开启唤醒词。
- 建议保留人工关闭开关或直接拔掉 Audio2Rig 输出。
- 单次发射应设置最长时长和冷却时间，避免异常长时间占用频道。

## 当前限制

- VAD 使用能量阈值实现，简单稳定，但不如 WebRTC VAD/Silero VAD 精细。
- `pyttsx3` 输出格式取决于操作系统语音引擎，某些环境可能需要调试。
- VOX 时序依赖 Audio2Rig/对讲机硬件，正式场景建议用串口 PTT。
- `sounddevice` 需要系统音频后端正常工作。

## 开发测试

```bash
pip install -e '.[dev]'
pytest
python -m compileall hamrobot
```
