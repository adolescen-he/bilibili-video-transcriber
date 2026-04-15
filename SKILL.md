---
name: bilibili-video-transcriber
description: 专业处理B站视频字幕问题，支持语音转文字、字幕下载、内容分析。基于实际B站字幕系统错误问题开发，提供完整的解决方案。
metadata:
  clawdbot:
    emoji: "🎬"
    requires:
      anyBins:
        - python3
        - ffmpeg
    os:
      - linux
      - darwin
      - win32
---

# 🎬 B站视频转录专家

**专业处理B站视频字幕问题，支持语音转文字、字幕下载、内容分析**

## 📋 功能特性

### ✅ 核心功能
1. **智能字幕处理**：自动检测B站字幕系统状态，智能选择最佳方案
2. **语音转文字**：使用Whisper模型进行高精度语音识别
3. **国内镜像支持**：自动使用国内镜像源，解决网络问题
4. **错误处理**：自动检测字幕关联错误，切换到语音转文字
5. **批量处理**：支持批量处理多个B站视频

### 🔧 技术特点
- **绕过B站字幕系统**：直接处理音频，避免字幕关联错误
- **多模型支持**：Whisper base/small/medium模型可选
- **Cookie管理**：支持Cookie文件管理和自动刷新
- **进度显示**：实时显示下载和转录进度
- **结果验证**：自动验证转录内容与视频标题相关性

## 🚀 快速开始

### 1. 安装依赖
```bash
# 安装技能包
clawhub install bilibili-transcriber-pro

# 或手动安装依赖
pip install bilibili-api requests pydub faster-whisper
```

### 2. 配置Cookie
```bash
# 创建Cookie文件
echo "SESSDATA=xxx; bili_jct=xxx; buvid3=xxx; DedeUserID=xxx" > ~/.bilibili_cookie.txt
```

### 3. 基本使用
```bash
# 处理单个视频
bilibili-transcribe BV1txQGByERW

# 指定Cookie文件
bilibili-transcribe BV1txQGByERW --cookie ~/.bilibili_cookie.txt

# 批量处理
bilibili-transcribe --batch bv_list.txt
```

## 📖 详细用法

### 命令行工具
```bash
# 查看帮助
bilibili-transcribe --help

# 处理视频并保存结果
bilibili-transcribe BV1txQGByERW --output ./results

# 使用指定模型
bilibili-transcribe BV1txQGByERW --model medium

# 仅下载音频
bilibili-transcribe BV1txQGByERW --audio-only

# 检查字幕状态
bilibili-transcribe BV1txQGByERW --check-only
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

# 批量处理
results = transcriber.process_batch(
    bvids=["BV1txQGByERW", "BV1xxxxxxx"],
    output_dir="./batch_output"
)
```

## 🛠️ 配置选项

### 配置文件 `~/.config/bilibili_transcriber/config.yaml`
```yaml
# Cookie配置
cookie:
  file: "~/.bilibili_cookie.txt"
  auto_refresh: true
  refresh_interval: 86400  # 24小时

# 模型配置
model:
  name: "base"  # base/small/medium
  device: "cpu"  # cpu/cuda
  compute_type: "int8"
  language: "zh"

# 网络配置
network:
  hf_endpoint: "https://hf-mirror.com"
  timeout: 30
  retry_times: 3

# 输出配置
output:
  default_dir: "./bilibili_transcripts"
  save_audio: true
  save_subtitles: true
  format: "txt"  # txt/json/markdown

# 验证配置
validation:
  keyword_match_threshold: 0.3
  min_transcript_length: 50
  check_duration_match: true
```

## 📊 输出格式

### 1. 文本格式 (`transcript.txt`)
```
[0.00s -> 3.90s] 兄弟们HermesAgent刚刚发布了更新4.13
[3.90s -> 5.76s] 那么这一次最大的一个升级呢
[5.76s -> 9.00s] 是它带来了本地的外部控制面板
...
```

### 2. JSON格式 (`transcript.json`)
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
    },
    ...
  ],
  "metadata": {
    "model": "base",
    "language": "zh",
    "processing_time": 45.2
  }
}
```

### 3. Markdown格式 (`summary.md`)
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

**完整转录**
[0.00s -> 3.90s] 兄弟们HermesAgent刚刚发布了更新4.13
...
```

## 🔍 高级功能

### 1. 字幕验证系统
```python
# 自动验证字幕准确性
validator = SubtitleValidator()
result = validator.validate(
    transcript=transcript_text,
    video_title=video_title,
    keywords=["HermesAgent", "WebUI", "控制面板"]
)

if result["is_valid"]:
    print(f"✅ 字幕验证通过: {result['match_rate']:.1%} 匹配度")
else:
    print(f"⚠️ 字幕可能有问题: {result['match_rate']:.1%} 匹配度")
```

### 2. 批量处理
```bash
# 创建视频列表文件
echo "BV1txQGByERW" > bv_list.txt
echo "BV1xxxxxxx" >> bv_list.txt

# 批量处理
bilibili-transcribe --batch bv_list.txt --parallel 3
```

### 3. 结果分析
```python
from bilibili_transcriber.analyzer import TranscriptAnalyzer

analyzer = TranscriptAnalyzer()
analysis = analyzer.analyze(transcript_text)

print(f"总时长: {analysis['duration']}秒")
print(f"段落数: {analysis['segment_count']}")
print(f"关键词: {analysis['top_keywords']}")
print(f"摘要: {analysis['summary']}")
```

## ⚙️ 故障排除

### 常见问题

#### 1. Cookie失效
```bash
# 重新获取Cookie
bilibili-transcribe --update-cookie

# 手动设置Cookie
export BILIBILI_COOKIE="SESSDATA=xxx; bili_jct=xxx"
```

#### 2. 网络问题
```bash
# 使用代理
bilibili-transcribe BV1txQGByERW --proxy http://127.0.0.1:7890

# 切换镜像源
bilibili-transcribe BV1txQGByERW --mirror https://mirror.example.com
```

#### 3. 模型下载失败
```bash
# 使用本地模型
bilibili-transcribe BV1txQGByERW --model-path ./local_models/

# 跳过模型下载检查
bilibili-transcribe BV1txQGByERW --skip-model-check
```

### 调试模式
```bash
# 启用详细日志
bilibili-transcribe BV1txQGByERW --verbose

# 调试模式
bilibili-transcribe BV1txQGByERW --debug

# 保存中间文件
bilibili-transcribe BV1txQGByERW --keep-temp
```

## 📈 性能优化

### 1. 缓存机制
```python
# 启用缓存
transcriber = BilibiliTranscriber(
    use_cache=True,
    cache_dir="~/.cache/bilibili_transcriber",
    cache_ttl=3600  # 1小时
)
```

### 2. 并行处理
```bash
# 并行处理多个视频
bilibili-transcribe --batch bv_list.txt --parallel 4

# 指定线程数
bilibili-transcribe BV1txQGByERW --threads 2
```

### 3. 资源限制
```bash
# 限制内存使用
bilibili-transcribe BV1txQGByERW --max-memory 2G

# 限制CPU使用
bilibili-transcribe BV1txQGByERW --cpu-limit 50%
```

## 🔗 集成示例

### 1. 与OpenClaw集成
```python
from openclaw.skills import bilibili_transcriber

@skill("bilibili-transcribe")
def handle_bilibili_transcribe(request):
    """处理B站视频转录请求"""
    bvid = request.params.get("bvid")
    
    # 调用转录功能
    result = bilibili_transcriber.process(bvid)
    
    # 返回结果
    return {
        "success": True,
        "data": result
    }
```

### 2. 自动化工作流
```yaml
# workflow.yaml
name: B站视频处理流水线
steps:
  - name: 下载视频
    action: bilibili-transcribe
    params:
      bvid: "{{ input.bvid }}"
      output: "./raw"
  
  - name: 内容分析
    action: analyze-transcript
    params:
      input: "./raw/transcript.txt"
      output: "./analysis"
  
  - name: 生成报告
    action: generate-report
    params:
      analysis: "./analysis"
      template: "video_report.md"
```

## 📚 使用案例

### 案例1：技术教程转录
```bash
# 转录AI技术教程
bilibili-transcribe BV1txQGByERW --output ./ai_tutorials

# 生成学习笔记
bilibili-transcribe BV1txQGByERW --format markdown --template study_note.md
```

### 案例2：内容分析
```python
# 分析多个视频内容
from bilibili_transcriber import BatchAnalyzer

analyzer = BatchAnalyzer()
results = analyzer.analyze_batch(
    bvids=["BV1txQGByERW", "BV1xxxxxxx"],
    analysis_types=["keywords", "summary", "sentiment"]
)

# 生成对比报告
report = analyzer.generate_comparison_report(results)
```

### 案例3：自动化监控
```python
# 监控特定UP主的新视频
from bilibili_transcriber.monitor import VideoMonitor

monitor = VideoMonitor(
    up_mid="12345678",  # UP主ID
    check_interval=3600,  # 每小时检查一次
    callback=process_new_video
)

monitor.start()
```

## 🧪 测试

### 单元测试
```bash
# 运行测试
python -m pytest tests/

# 测试特定功能
python -m pytest tests/test_download.py
python -m pytest tests/test_transcribe.py
```

### 集成测试
```bash
# 测试完整流程
python -m pytest tests/integration/test_full_flow.py

# 使用测试Cookie
BILIBILI_TEST_COOKIE="test_cookie" python -m pytest
```

## 📄 许可证

MIT License

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📞 支持

- 问题反馈: GitHub Issues
- 文档: https://github.com/yourname/bilibili-transcriber-pro
- 讨论: Discord/微信群

---

**基于实际经验开发，专门解决B站字幕系统错误问题，稳定可靠！**