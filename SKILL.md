---
name: bilibili-video-transcriber
description: 【B站字幕获取】专业处理 B 站视频字幕问题，支持语音转文字、字幕下载、内容分析。基于实际 B 站字幕系统错误问题开发，提供完整的解决方案。
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
1. **智能字幕优先**：自动按优先级获取（CC 字幕 → AI 字幕 → 音频转录 → 视频下载）
2. **Cookie 安全存储**：多路径冗余存储 + immutable 写保护，防止误删
3. **自动失效检测**：每次处理视频前自动验证 Cookie 有效性
4. **飞书扫码通知**：Cookie 失效时自动生成二维码并通过飞书发送
5. **语音转文字**：使用 Whisper/Vosk 模型进行高精度语音识别
6. **国内镜像支持**：自动使用国内镜像源
7. **批量处理**：支持批量处理多个 B 站视频
8. **大会员支持**：支持扫码登录获取大会员权限

### 🔧 Cookie 安全机制
```
存储路径（3重冗余）:
  1. 技能目录: ~/.openclaw/workspace/skills/.../.bilibili_cookie  ← immutable 保护
  2. 用户目录: ~/.bilibili_cookie_storage
  3. 配置目录: ~/.config/bilibili_transcriber/cookie
  
运行引用: ~/.bilibili_cookie.txt（自动同步，600权限）

失效时: → 自动检测 → 生成二维码 → 通过飞书发送 → 用户扫码 → 自动保存
```

## 🚀 快速开始

### 1. 安装依赖
```bash
# 安装技能包
clawhub install bilibili-transcriber-pro

# 或手动安装依赖
pip install bilibili-api requests pydub faster-whisper vosk qrcode
```

### 2. 扫码登录（推荐）
```bash
# 扫码登录（会自动保存到冗余存储）
bilibili-transcribe --login

# 检查登录状态
bilibili-transcribe --check-cookie
```

### 3. 基本使用
```bash
# 处理单个视频（自动验证Cookie，含评论获取）
bilibili-transcribe BV1txQGByERW

# 指定Cookie文件
bilibili-transcribe BV1txQGByERW --cookie ~/.bilibili_cookie.txt

# 批量处理
bilibili-transcribe --batch bv_list.txt
```

### 4. 输出特点：评论获取
```bash
# 处理视频时会自动获取热门评论（按点赞排序），包含：
# - 热评内容 + 点赞数
# - 热评下的回复
# - 评论写入 markdown 的 💬 评论区部分
# - CLI 直接展示前3条热评预览
```

## 📖 详细用法

### Cookie 管理（新增）
```bash
# 扫码登录（推荐方式）
bilibili-transcribe --login

# 检查Cookie状态
bilibili-transcribe --check-cookie
# 输出示例：
#   ✅ Cookie 有效
#   👤 用户: 你的B站用户名
#   🏆 大会员: ✅
#   📂 存储路径: ~/.bilibili_cookie.txt

# 手动更新Cookie
bilibili-transcribe --update-cookie "SESSDATA=xxx; bili_jct=xxx"

# 设置环境变量
export BILIBILI_COOKIE="SESSDATA=xxx; bili_jct=xxx"
```

### Python API（Cookie 管理）
```python
from cookie_manager import (
    save_cookie, load_cookie, check_cookie_valid,
    needs_cookie_refresh, BilibiliQRLogin, send_qr_via_feishu
)

# 检查Cookie是否需要刷新
reason = needs_cookie_refresh()
if reason:
    print(f"⚠️ Cookie 需要刷新: {reason}")
    login = BilibiliQRLogin()
    qr_path = login.generate_qr_code()
    
    # 通过飞书发送二维码
    send_qr_via_feishu(qr_path)
    
    # 轮询等待扫码
    result = login.poll_login()
    if result['success']:
        print(f"✅ 登录成功: {result['username']}")
else:
    print("✅ Cookie 有效")
```

## 🛠️ 配置选项

### 配置文件 `~/.config/bilibili_transcriber/config.yaml`
```yaml
# Cookie 配置（增强版）
cookie:
  file: "~/.bilibili_cookie.txt"
  auto_refresh: true
  refresh_interval: 86400  # 24 小时
  redundant_storage: true   # 启用冗余存储
  storage_paths:
    - "~/.openclaw/workspace/skills/bilibili-video-transcriber/.bilibili_cookie"
    - "~/.bilibili_cookie_storage"
    - "~/.config/bilibili_transcriber/cookie"
  notify_on_expire: true    # Cookie失效时通知
  notify_channel: "feishu"  # 通知通道

# 模型配置
model:
  engine: "whisper"
  name: "base"
  device: "cpu"
  compute_type: "int8"
  language: "zh"

# 飞书通知配置
notify:
  channel: "feishu"  # 通知通道
  qr_temp_dir: "/tmp"
```

## 📊 输出格式

### 0. 评论获取（新增）
处理视频时自动按**点赞排序**获取热门评论，最多 30 条热评 + 每条热评 3 条回复。
- 数据保存在 markdown 的 `💬 热门评论` 部分
- JSON 格式包含 `comments` 数组
- CLI 输出展示前 3 条热评预览

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
    "title": "视频标题",
    "duration": 210,
    "up": "UP主名"
  },
  "transcript": [
    {"start": 0.0, "end": 3.9, "text": "内容", "confidence": 0.95}
  ],
  "cookie_status": {
    "valid": true,
    "user": "用户名",
    "is_vip": true
  }
}
```

### 3. Markdown 格式 (`summary.md`)
```markdown
# 视频标题

**视频信息**
- BV 号：BV1xxx
- 时长：210 秒
- UP 主：xxx
- Cookie 状态：✅ 有效 (用户: xxx)

**核心内容**
1. 要点一
2. 要点二

**完整转录**
[0.00s -> 3.90s] 内容
...
```

## 🔧 Cookie 管理详解

### 冗余存储机制
```
cookie_manager.py 负责管理 Cookie 的存储和生命周期：

┌─────────────────────────────────────────────────┐
│                  cookie_manager                   │
├─────────────────────────────────────────────────┤
│  1. save_cookie(cookie_str)                      │
│     → 写入活跃文件 (~/.bilibili_cookie.txt)      │
│     → 同步到3个冗余路径（含 immutable 保护）     │
│     → 设置 600 权限                              │
├─────────────────────────────────────────────────┤
│  2. load_cookie()                                │
│     → 依次查找所有存储路径                        │
│     → 如果从备份读到，自动补全到活跃路径          │
│     → 也检查环境变量 BILIBILI_COOKIE             │
├─────────────────────────────────────────────────┤
│  3. check_cookie_valid(cookie_str)               │
│     → 调用 bilibili_api 验证有效期               │
│     → 返回 {valid, username, is_vip, error}      │
├─────────────────────────────────────────────────┤
│  4. needs_cookie_refresh()                       │
│     → 快速检查是否需要刷新                        │
│     → 返回 None=有效, str=失效原因               │
├─────────────────────────────────────────────────┤
│  5. BilibiliQRLogin                              │
│     → generate_qr_code() → 生成二维码图片        │
│     → poll_login() → 轮询扫码结果               │
│     → poll_once() → 单次检查（供外部调用）       │
├─────────────────────────────────────────────────┤
│  6. send_qr_via_feishu(image_path)               │
│     → 写入信号文件（供代理处理器读取并发送）     │
└─────────────────────────────────────────────────┘
```

### 飞书扫码登录流程
```
1. 用户发送 B 站链接 or 调用 --login
2. cookie_manager 检测到 Cookie 不存在/失效
3. BilibiliQRLogin 生成二维码图片
4. send_qr_via_feishu 写入信号文件
5. [代理处理器] 读取信号 → 上传飞书图片 → 发送给用户
6. 用户扫码 → poll_login 轮询到成功
7. save_cookie 保存到冗余存储
8. 继续处理视频
```

### 安全特性
- **权限 600**：仅文件所有者可读写
- **chattr +i**：对技能目录内的 Cookie 设置 immutable 标记，不可删除/修改
- **多路径冗余**：3个独立存储位置，任一被删都能从其他路径恢复
- **自动恢复**：load_cookie 发现活跃文件被删时，自动从备份恢复

## 🔗 与其他技能的集成

### 与 cookie_manager 的集成
```python
# 在任何脚本中都可以使用
from cookie_manager import (
    save_cookie, load_cookie, check_cookie_valid,
    needs_cookie_refresh
)

# 获取当前 Cookie（自动加载、自动恢复）
cookie_str = load_cookie()
if cookie_str:
    status = check_cookie_valid(cookie_str)
    print(f"用户: {status['username']}, 有效: {status['valid']}")
```

## 🔍 故障排除

### Cookie 相关问题

#### 1. 提示 "Cookie 已失效"
```bash
# 重新扫码登录
bilibili-transcribe --login

# 或手动更新
bilibili-transcribe --update-cookie "SESSDATA=xxx; bili_jct=xxx"
```

#### 2. Cookie 文件被误删
```
不用担心，cookie_manager 会自动从备份路径恢复。
备份位置：
  ~/.openclaw/workspace/skills/bilibili-video-transcriber/.bilibili_cookie
  ~/.bilibili_cookie_storage
  ~/.config/bilibili_transcriber/cookie

技能目录内的备份设置了 immutable 保护，不可删除。
```

#### 3. 检查 Cookie 存储状态
```bash
bilibili-transcribe --check-cookie
```

## 📄 许可证

MIT License

---

**最后更新：** 2026-05-07

**本次更新内容：**
1. ✅ 新增 `get_comments()` 方法：自动获取视频热门评论（按热度排序）
2. ✅ `ProcessingResult` 新增 `comments` 字段
3. ✅ `save_transcript()` markdown 格式新增 `💬 热门评论` 区块
4. ✅ `print_result()` CLI 输出展示前 3 条热评
5. ✅ 评论获取非关键步骤，失败不影响主流程
6. ✅ 支持热评下的回复获取
