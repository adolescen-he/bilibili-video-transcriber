# 🎬 B站视频转录专家

**专业处理B站视频字幕问题，支持语音转文字、字幕下载、内容分析**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ 特性

### 🎯 核心功能
- **智能字幕处理**：自动检测B站字幕系统状态，智能选择最佳方案
- **语音转文字**：使用Whisper模型进行高精度语音识别
- **国内镜像支持**：自动使用国内镜像源，解决网络问题
- **错误处理**：自动检测字幕关联错误，切换到语音转文字
- **批量处理**：支持批量处理多个B站视频

### 🔧 技术特点
- **绕过B站字幕系统**：直接处理音频，避免字幕关联错误
- **多模型支持**：Whisper base/small/medium模型可选
- **Cookie管理**：支持Cookie文件管理和自动刷新
- **进度显示**：实时显示下载和转录进度
- **结果验证**：自动验证转录内容与视频标题相关性

## 🚀 快速开始

### 安装

```bash
# 1. 下载技能包
git clone https://github.com/community/bilibili-transcriber-pro.git
cd bilibili-transcriber-pro

# 2. 运行安装脚本
python setup.py

# 或手动安装
pip install -r requirements.txt
```

### 配置Cookie

```bash
# 编辑Cookie文件
nano ~/.bilibili_cookie.txt

# 添加你的B站Cookie（从浏览器开发者工具获取）
# 格式: SESSDATA=xxx; bili_jct=xxx; buvid3=xxx; DedeUserID=xxx
```

### 基本使用

```bash
# 处理单个视频
bilibili-transcribe BV1txQGByERW

# 指定Cookie文件
bilibili-transcribe BV1txQGByERW --cookie ~/.bilibili_cookie.txt

# 批量处理
bilibili-transcribe --batch bv_list.txt
```

## 📖 详细文档

### 命令行参数

```bash
# 查看完整帮助
bilibili-transcribe --help

# 处理视频
bilibili-transcribe <BV号> [选项]

# 常用选项
--model <base|small|medium>    # 选择模型（默认: base）
--format <txt|json|markdown>   # 输出格式（默认: txt）
--output <目录>                # 输出目录（默认: ./bilibili_transcripts）
--keep-audio                   # 保留音频文件
--verbose                      # 详细输出
--debug                        # 调试模式
```

### Python API

```python
from bilibili_transcriber import BilibiliTranscriber

# 初始化
transcriber = BilibiliTranscriber(
    cookie_file="~/.bilibili_cookie.txt",
    model="base",
    use_china_mirror=True
)

# 处理视频
result = transcriber.process(
    bvid="BV1txQGByERW",
    output_dir="./output"
)

if result.success:
    print(f"✅ 处理成功: {result.video_info.title}")
    print(f"📄 转录文件: {result.transcript_path}")
    print(f"⏰ 处理时间: {result.processing_time:.2f}秒")
```

## 🎯 使用案例

### 案例1：技术教程转录

```bash
# 转录AI技术教程
bilibili-transcribe BV1txQGByERW --output ./ai_tutorials

# 生成学习笔记
bilibili-transcribe BV1txQGByERW --format markdown
```

### 案例2：内容分析

```python
# 分析多个视频内容
from bilibili_transcriber import BilibiliTranscriber

transcriber = BilibiliTranscriber()
bvids = ["BV1txQGByERW", "BV1xxxxxxx"]

for bvid in bvids:
    result = transcriber.process(bvid)
    if result.success:
        print(f"✅ {bvid}: {result.video_info.title}")
```

### 案例3：自动化监控

```python
# 监控特定UP主的新视频
import time
from bilibili_transcriber import BilibiliTranscriber

def check_new_videos(up_mid):
    # 实现视频检查逻辑
    pass

while True:
    check_new_videos("12345678")
    time.sleep(3600)  # 每小时检查一次
```

## ⚙️ 配置

配置文件位置：`~/.config/bilibili_transcriber/config.yaml`

```yaml
# 模型配置
model:
  name: "base"           # base/small/medium
  device: "cpu"          # cpu/cuda
  compute_type: "int8"   # int8/float16/float32
  language: "zh"         # 语言代码

# 网络配置
network:
  hf_endpoint: "https://hf-mirror.com"  # 国内镜像
  timeout: 30
  retry_times: 3

# 输出配置
output:
  default_dir: "./bilibili_transcripts"
  save_audio: true
  format: "txt"          # txt/json/markdown
```

## 🔍 故障排除

### 常见问题

#### 1. Cookie失效
```bash
# 检查Cookie状态
bilibili-transcribe --check-cookie

# 更新Cookie
bilibili-transcribe --update-cookie "SESSDATA=xxx; bili_jct=xxx"
```

#### 2. 网络问题
```bash
# 使用代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
bilibili-transcribe BV1txQGByERW
```

#### 3. 模型下载失败
```bash
# 使用国内镜像
export HF_ENDPOINT="https://hf-mirror.com"
bilibili-transcribe BV1txQGByERW
```

### 调试模式

```bash
# 启用详细日志
bilibili-transcribe BV1txQGByERW --verbose --debug

# 查看日志文件
tail -f bilibili_transcriber.log
```

## 📊 输出示例

### 文本格式
```
[0.00s -> 3.90s] 兄弟们HermesAgent刚刚发布了更新4.13
[3.90s -> 5.76s] 那么这一次最大的一个升级呢
[5.76s -> 9.00s] 是它带来了本地的外部控制面板
...
```

### JSON格式
```json
{
  "video_info": {
    "bvid": "BV1txQGByERW",
    "title": "HermesAgent突然上WebUI了！这一波，体验直接拉满",
    "duration": 210,
    "up": "磊哥聊AI"
  },
  "transcript": [
    {
      "start": 0.0,
      "end": 3.9,
      "text": "兄弟们HermesAgent刚刚发布了更新4.13",
      "confidence": 0.95
    }
  ]
}
```

### Markdown格式
```markdown
# HermesAgent突然上WebUI了！这一波，体验直接拉满

**视频信息**
- BV号: BV1txQGByERW
- 时长: 210秒
- UP主: 磊哥聊AI
- 处理时间: 2026-04-15 08:16:00

**核心内容**
1. HermesAgent 4.13版本发布
2. 新增本地WebUI控制面板
3. 支持中英文界面
4. 提供状态监控、会话管理等功能
```

## 🏗️ 架构设计

```
bilibili-transcriber-pro/
├── bilibili_transcriber.py    # 核心处理模块
├── cli.py                     # 命令行接口
├── config.yaml                # 配置文件
├── setup.py                   # 安装脚本
├── requirements.txt           # 依赖列表
├── README.md                  # 说明文档
├── SKILL.md                   # 技能文档
├── package.json               # 包配置
├── test_install.py            # 测试脚本
└── examples/                  # 示例文件
    ├── bv_list.txt           # BV号列表示例
    └── README.md             # 使用示例
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证

## 🙏 致谢

- [bilibili-api](https://github.com/MoyuScript/bilibili-api) - B站API封装
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 快速Whisper实现
- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型

## 📞 支持

- 问题反馈: GitHub Issues
- 文档: README.md
- 示例: examples/

---

**基于实际经验开发，专门解决B站字幕系统错误问题，稳定可靠！**