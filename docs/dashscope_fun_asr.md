# DashScope Fun-ASR 本地文件识别

HamRobot 支持通过阿里云 DashScope SDK 调用 `fun-asr-realtime`，直接识别本地 wav 文件。

当前集成方式基于官方示例：

```python
from dashscope.audio.asr import Recognition

recognition = Recognition(
    model='fun-asr-realtime',
    format='wav',
    sample_rate=16000,
    callback=None,
)
result = recognition.call('asr_example.wav')
print(result.get_sentence())
```

## 配置

在 `config/config.local.yaml` 中配置：

```yaml
asr:
  engine: dashscope_realtime_file
  dashscope_api_key: "你的百炼API Key"
  dashscope_model: fun-asr-realtime
  dashscope_format: wav
  dashscope_sample_rate: 16000
  dashscope_base_websocket_api_url: "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
```

## 运行流程

```text
Audio2Rig录音
  ↓
HamRobot VAD切句并保存本地 wav
  ↓
DashScope Recognition.call(local_wav)
  ↓
返回识别文本
  ↓
LLM + TTS + Audio2Rig 发射
```

该方案不需要 OSS，不需要公网音频 URL，也不需要本地 HTTP 服务。

## 注意事项

- 录音格式建议保持为 16kHz、单声道、16-bit PCM wav。
- `dashscope_sample_rate` 应与 HamRobot 的 `audio.sample_rate` 一致。
- 仓库示例配置中不要写真实 API Key，建议复制为 `config.local.yaml` 后在本地填写。
- 该实现仍然是“录完一句后识别本地 wav”，不是真正的边说边出 partial 文本的流式状态机。
