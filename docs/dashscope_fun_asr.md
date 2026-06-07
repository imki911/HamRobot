# DashScope Fun-ASR 本地文件识别

HamRobot 支持通过阿里云 DashScope SDK 调用 `fun-asr-realtime`，直接识别本地 wav 文件，并可在每次识别时临时创建热词表来提升 HAM 呼号和专有词识别概率。

当前识别方式基于官方示例：

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

热词方式基于 `VocabularyService`：

```python
from dashscope.audio.asr import VocabularyService

service = VocabularyService()
vocabulary_id = service.create_vocabulary(
    prefix='hamrobot',
    target_model='fun-asr-realtime',
    vocabulary=[{'text': 'BH4HZU', 'weight': 5}],
)
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
  dashscope_base_http_api_url: "https://dashscope.aliyuncs.com/api/v1"
  dashscope_base_websocket_api_url: "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

  dashscope_vocabulary_enabled: true
  dashscope_vocabulary_prefix: hamrobot
  dashscope_vocabulary_delete_after_call: true
  dashscope_vocabulary:
    - { text: "BH4HZU", weight: 5 }
    - { text: "CQ", weight: 4 }
    - { text: "DE", weight: 4 }
    - { text: "QTH", weight: 4 }
    - { text: "QSL", weight: 4 }
    - { text: "OVER", weight: 4 }
    - { text: "昆山", weight: 3 }
    - { text: "周庄", weight: 3 }
```

## 运行流程

```text
Audio2Rig录音
  ↓
HamRobot VAD切句并保存本地 wav
  ↓
创建 DashScope 热词表
  ↓
DashScope Recognition.call(local_wav, vocabulary_id)
  ↓
删除热词表，避免占用配额
  ↓
返回识别文本
  ↓
LLM + TTS + Audio2Rig 发射
```

## 热词建议

建议把这些内容加入热词表：

- 你的呼号，例如 `BH4HZU`
- 常见通联词：`CQ`、`DE`、`QTH`、`QSL`、`QRZ`、`OVER`、`ROGER`、`73`
- 本地地名：`昆山`、`周庄`
- 设备和天线词：`泉盛`、`晾衣杆天线`
- 高频联系人呼号和社群专有名词

权重建议：

```text
5：自己的呼号、强专有名词
4：CQ/DE/QTH/QSL/OVER 等 HAM 关键词
3：地名、设备名、普通专有词
```

## 注意事项

- 录音格式建议保持为 16kHz、单声道、16-bit PCM wav。
- `dashscope_sample_rate` 应与 HamRobot 的 `audio.sample_rate` 一致。
- 仓库示例配置中不要写真实 API Key，建议复制为 `config.local.yaml` 后在本地填写。
- 默认每次识别后删除热词表，避免占用配额。
- 如果你希望减少创建热词表带来的延迟，可以后续改成启动时创建并复用，程序退出时删除。
- 该实现仍然是“录完一句后识别本地 wav”，不是真正的边说边出 partial 文本的流式状态机。
