---
name: bilibili-video-transcriber
description: 专业处理 B 站视频字幕问题，支持语音转文字、字幕下载、内容分析。基于实际 B 站字幕系统错误问题开发，提供完整的解决方案。
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

# 🎬 B 站视频转录专家

**专业处理 B 站视频字幕问题，支持语音转文字、字幕下载、内容分析**

## 📋 功能特性

### ✅ 核心功能
1. **智能字幕处理**：自动检测 B 站字幕系统状态，智能选择最佳方案
2. **语音转文字**：使用 Whisper/Vosk 模型进行高精度语音识别
3. **国内镜像支持**：自动使用国内镜像源，解决网络问题
4. **错误处理**：自动检测字幕关联错误，切换到语音转文字
5. **批量处理**：支持批量处理多个 B 站视频
6. **大会员支持**：支持扫码登录获取大会员权限，下载高音质视频

### 🔧 技术特点
- **绕过 B 站字幕系统**：直接处理音频，避免字幕关联错误
- **多模型支持**：Whisper base/small/medium 或 Vosk 离线模型
- **Cookie 管理**：支持扫码登录和 Cookie 文件管理
- **进度显示**：实时显示下载和转录进度
- **结果验证**：自动验证转录内容与视频标题相关性
- **镜像自动切换**：模型下载失败时自动切换到国内镜像源

## 🚀 快速开始

### 1. 安装依赖
```bash
# 安装技能包
clawhub install bilibili-transcriber-pro

# 或手动安装依赖
pip install bilibili-api requests pydub faster-whisper vosk qrcode
```

### 2. 配置 Cookie
```bash
# 方式 1：扫码登录（推荐）
bilibili-transcribe --login

# 方式 2：手动创建 Cookie 文件
echo "SESSDATA=xxx; bili_jct=xxx; buvid3=xxx; DedeUserID=xxx" > ~/.bilibili_cookie.txt
```

### 3. 基本使用
```bash
# 处理单个视频
bilibili-transcribe BV1txQGByERW

# 指定 Cookie 文件
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

# 使用 Vosk 离线模型（无需网络）
bilibili-transcribe BV1txQGByERW --engine vosk

# 仅下载音频
bilibili-transcribe BV1txQGByERW --audio-only

# 检查字幕状态
bilibili-transcribe BV1txQGByERW --check-only

# 扫码登录
bilibili-transcribe --login
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
# Cookie 配置
cookie:
  file: "~/.bilibili_cookie.txt"
  auto_refresh: true
  refresh_interval: 86400  # 24 小时

# 模型配置
model:
  engine: "whisper"  # whisper/vosk
  name: "base"  # base/small/medium (whisper) 或 vosk-model-small-cn-0.22 (vosk)
  device: "cpu"  # cpu/cuda
  compute_type: "int8"
  language: "zh"

# 网络配置
network:
  hf_endpoint: "https://hf-mirror.com"
  auto_switch_mirror: true  # 自动切换镜像源
  mirrors:
    - "https://huggingface.co"
    - "https://hf-mirror.com"
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
[0.00s -> 3.90s] 兄弟们 HermesAgent 刚刚发布了更新 4.13
[3.90s -> 5.76s] 那么这一次最大的一个升级呢
[5.76s -> 9.00s] 是它带来了本地的外部控制面板
...
```

### 2. JSON 格式 (`transcript.json`)
```json
{
  "video_info": {
    "bvid": "BV1txQGByERW",
    "title": "HermesAgent 突然上 WebUI 了！这一波，体验直接拉满",
    "duration": 210,
    "up": "磊哥聊 AI"
  },
  "transcript": [
    {
      "start": 0.0,
      "end": 3.9,
      "text": "兄弟们 HermesAgent 刚刚发布了更新 4.13",
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

### 3. Markdown 格式 (`summary.md`)
```markdown
# HermesAgent 突然上 WebUI 了！这一波，体验直接拉满

**视频信息**
- BV 号：BV1txQGByERW
- 时长：210 秒
- UP 主：磊哥聊 AI
- 处理时间：2026-04-15 08:16:00

**核心内容**
1. HermesAgent 4.13 版本发布
2. 新增本地 WebUI 控制面板
3. 支持中英文界面
4. 提供状态监控、会话管理等功能

**完整转录**
[0.00s -> 3.90s] 兄弟们 HermesAgent 刚刚发布了更新 4.13
...
```

## 🔍 高级功能

### 1. 扫码登录（大会员支持）
```python
from bilibili_transcriber import BilibiliLogin

# 生成二维码
login = BilibiliLogin()
qr_url = login.generate_qr()
print(f"请用 B 站 APP 扫码：{qr_url}")

# 验证登录状态
result = login.poll()
if result['success']:
    print(f"登录成功！用户：{result['username']}")
    print(f"大会员状态：{'✅' if result['is_vip'] else '❌'}")
    print(f"Cookie 已保存到：~/.bilibili_cookie.txt")
```

### 2. 镜像源自动切换
```python
import os
from faster_whisper import WhisperModel

def load_model_with_retry(model_name, device="cpu", compute_type="int8"):
    """加载模型，失败时自动切换到国内镜像"""
    mirrors = [
        ("原始源", "https://huggingface.co"),
        ("国内镜像", "https://hf-mirror.com"),
    ]
    
    for name, mirror in mirrors:
        try:
            if mirror != "https://huggingface.co":
                print(f"🔄 切换到镜像源：{mirror}")
                os.environ['HF_ENDPOINT'] = mirror
            
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            print(f"✅ 模型加载成功：{model_name} (来源：{name})")
            return model
            
        except Exception as e:
            print(f"❌ 镜像源 {name} 失败：{e}")
    
    raise Exception("所有镜像源都失败，请检查网络连接")

# 使用示例
model = load_model_with_retry("base", device="cpu", compute_type="int8")
```

### 3. Vosk 离线转录（无需网络）
```python
from vosk import Model, KaldiRecognizer
import wave

# 加载离线模型
model = Model("/root/.cache/vosk/vosk-model-small-cn-0.22")

# 转录音频
wf = wave.open("audio.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

transcript = []
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        transcript.append(result['text'])

final_result = json.loads(rec.FinalResult())
if final_result.get('text'):
    transcript.append(final_result['text'])

print("转录完成：", " ".join(transcript))
```

### 4. 字幕验证系统
```python
# 自动验证字幕准确性
validator = SubtitleValidator()
result = validator.validate(
    transcript=transcript_text,
    video_title=video_title,
    keywords=["HermesAgent", "WebUI", "控制面板"]
)

if result["is_valid"]:
    print(f"✅ 字幕验证通过：{result['match_rate']:.1%} 匹配度")
else:
    print(f"⚠️ 字幕可能有问题：{result['match_rate']:.1%} 匹配度")
```

### 5. 批量处理
```bash
# 创建视频列表文件
echo "BV1txQGByERW" > bv_list.txt
echo "BV1xxxxxxx" >> bv_list.txt

# 批量处理
bilibili-transcribe --batch bv_list.txt --parallel 3
```

### 6. 结果分析
```python
from bilibili_transcriber.analyzer import TranscriptAnalyzer

analyzer = TranscriptAnalyzer()
analysis = analyzer.analyze(transcript_text)

print(f"总时长：{analysis['duration']}秒")
print(f"段落数：{analysis['segment_count']}")
print(f"关键词：{analysis['top_keywords']}")
print(f"摘要：{analysis['summary']}")
```

## ⚙️ 故障排除

### 常见问题

#### 1. Cookie 失效
```bash
# 重新获取 Cookie
bilibili-transcribe --update-cookie

# 手动设置 Cookie
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

#### 4. HuggingFace 下载失败（新增）
**问题：** 使用 faster-whisper 下载模型时出现 `ConnectError: [Errno 101] Network is unreachable`

**原因：** HuggingFace 服务器网络连接不稳定

**解决方案：**

**方案 1：自动切换到国内镜像**
```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

**方案 2：手动指定镜像源**
```bash
HF_ENDPOINT=https://hf-mirror.com python -m pip install faster-whisper
```

**方案 3：使用本地缓存模型**
```python
model = WhisperModel(
    "/root/.cache/huggingface/hub/models--Systran--faster-whisper-base",
    device="cpu",
    compute_type="int8"
)
```

**方案 4：使用 Vosk 离线模型（推荐）**
```bash
# Vosk 模型已缓存，无需网络
bilibili-transcribe BV1txQGByERW --engine vosk
```

#### 5. B 站 API 412 错误
**问题：** 调用 B 站 API 时返回 HTTP 412 Precondition Failed

**原因：** 缺少 WBI 签名或 Cookie 失效

**解决方案：**
1. 重新扫码登录获取新 Cookie
2. 使用大会员 Cookie（权限更高）
3. 添加 WBI 签名（代码自动处理）

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
    cache_ttl=3600  # 1 小时
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

# 限制 CPU 使用
bilibili-transcribe BV1txQGByERW --cpu-limit 50%
```

## 🔗 集成示例

### 1. 与 OpenClaw 集成
```python
from openclaw.skills import bilibili_transcriber

@skill("bilibili-transcribe")
def handle_bilibili_transcribe(request):
    """处理 B 站视频转录请求"""
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
name: B 站视频处理流水线
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

### 案例 1：技术教程转录
```bash
# 转录 AI 技术教程
bilibili-transcribe BV1txQGByERW --output ./ai_tutorials

# 生成学习笔记
bilibili-transcribe BV1txQGByERW --format markdown --template study_note.md
```

### 案例 2：内容分析
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

### 案例 3：自动化监控
```python
# 监控特定 UP 主的新视频
from bilibili_transcriber.monitor import VideoMonitor

monitor = VideoMonitor(
    up_mid="12345678",  # UP 主 ID
    check_interval=3600,  # 每小时检查一次
    callback=process_new_video
)

monitor.start()
```

### 案例 4：飞书知识库归档（新增）
```python
# 转录完成后自动归档到飞书知识库
from bilibili_transcriber import BilibiliTranscriber
from feishu_create_doc import create_wiki_doc

# 转录视频
transcriber = BilibiliTranscriber()
result = transcriber.process("BV1E7wtzaEdq")

# 整理为结构化文档
markdown_content = format_to_markdown(result)

# 创建飞书知识库文档
doc_url = create_wiki_doc(
    title="📚 视频转录：从 LLM 到 Agent Skill",
    markdown=markdown_content,
    wiki_space="7624328764398324948"  # AI 工具知识库
)

print(f"文档已创建：{doc_url}")
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

# 使用测试 Cookie
BILIBILI_TEST_COOKIE="test_cookie" python -m pytest
```

## 📝 实战经验总结

### 完整工作流（2026-04-19 更新）

**成功路径：**
```
B 站视频 → 扫码登录 → 获取 cookie → 下载视频 → 
ffmpeg 提取音频 → Vosk/Whisper 转录 → 整理结构化文档 → 
飞书知识库归档
```

**关键步骤：**

1. **B 站扫码登录**
   - 使用 `passport.bilibili.com` API 生成二维码
   - 轮询验证登录状态
   - 提取 cookie 并保存（Netscape 格式）
   - 大会员 cookie 有效期约 1 年

2. **视频下载**
   - 使用大会员 cookie 获取高音质视频
   - 注意 URL 有效期（需尽快下载）
   - 使用 wget 或 requests 下载

3. **音频提取**
   ```bash
   ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
   ```

4. **语音转录**
   - **Vosk（离线）**：无需网络，准确率~85%
   - **Whisper（在线）**：需要网络，准确率~95%
   - 采样率必须为 16000Hz

5. **结构化整理**
   - 按主题分组转录内容
   - 提取核心概念
   - 添加对比表格和示例
   - 提炼关键洞察

6. **知识库归档**
   - 使用 `feishu_create_doc` + `wiki_space` 参数
   - 支持 Markdown 格式
   - 自动添加目录和格式化

**技术栈：**
| 工具 | 用途 |
|------|------|
| requests | API 调用 |
| qrcode | 二维码生成 |
| ffmpeg | 音频提取 |
| vosk | 离线语音识别 |
| faster-whisper | 在线语音识别 |
| yt-dlp/wget | 视频下载 |
| 飞书 API | 知识库归档 |

**注意事项：**
- Cookie 需定期更新（有效期约 1 年）
- WBI 签名：B 站 API 需要动态签名
- Vosk 模型：提前下载缓存
- 飞书权限：确保有知识库写入权限
- 视频 URL：有有效期，需尽快下载

### 模型下载失败处理（2026-04-18 更新）

**问题：** HuggingFace 下载失败 `Network is unreachable`

**解决方案：**
1. 设置环境变量 `HF_ENDPOINT=https://hf-mirror.com`
2. 代码中自动切换镜像源
3. 使用本地缓存模型
4. 使用 Vosk 离线模型（推荐）

**代码实现：**
```python
def load_model_with_retry(model_name, device="cpu", compute_type="int8"):
    mirrors = [
        ("原始源", "https://huggingface.co"),
        ("国内镜像", "https://hf-mirror.com"),
    ]
    
    for name, mirror in mirrors:
        try:
            if mirror != "https://huggingface.co":
                os.environ['HF_ENDPOINT'] = mirror
            model = WhisperModel(model_name, device, compute_type)
            return model
        except Exception as e:
            continue
    raise Exception("所有镜像源失败")
```

## 📄 许可证

MIT License

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📞 支持

- 问题反馈：GitHub Issues
- 文档：https://github.com/yourname/bilibili-transcriber-pro
- 讨论：Discord/微信群

---

**基于实际经验开发，专门解决 B 站字幕系统错误问题，稳定可靠！**

**最后更新：** 2026-04-19
