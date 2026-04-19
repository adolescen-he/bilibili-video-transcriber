#!/usr/bin/env python3
"""
B 站视频转录专家 - 核心处理模块
专业处理 B 站视频字幕问题，支持语音转文字、字幕下载、内容分析

更新日志：
- 2026-04-19 v2.0: 优化下载优先级（字幕→AI 字幕→音频→视频）
- 2026-04-19 v2.0: 添加系统资源检测，智能选择模型
- 2026-04-19 v1.1: 添加镜像源自动切换功能
- 2026-04-19 v1.0: 添加 Vosk 离线引擎支持
"""

import os
import sys
import json
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import requests

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """视频信息"""
    bvid: str
    title: str
    duration: int
    up_name: str
    up_mid: str
    pubdate: int
    cid: int


@dataclass
class SubtitleResult:
    """字幕获取结果"""
    success: bool
    source: str  # "cc" / "ai" / "transcribe"
    transcript: Optional[List[Dict]] = None
    error: Optional[str] = None


@dataclass
class TranscriptSegment:
    """转录片段"""
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    video_info: Optional[VideoInfo] = None
    transcript: Optional[List[TranscriptSegment]] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    method_used: Optional[str] = None  # 使用的方法：cc_subtitle/ai_subtitle/audio_transcribe


class BilibiliTranscriber:
    """B 站视频转录器"""
    
    def __init__(
        self,
        cookie_file: Optional[str] = None,
        model_name: Optional[str] = None,  # None 表示自动选择
        device: Optional[str] = None,  # None 表示自动选择
        compute_type: str = "int8",
        use_china_mirror: bool = True,
        auto_switch_mirror: bool = True,
        output_dir: str = "./bilibili_transcripts",
        keep_audio: bool = True,
        language: str = "zh",
        prefer_offline: bool = False  # 优先使用离线方式
    ):
        """
        初始化转录器
        
        Args:
            cookie_file: B 站 Cookie 文件路径
            model_name: 模型名称 (None=自动选择 / base/small/medium / vosk 路径)
            device: 设备 (None=自动选择 / cpu/cuda)
            compute_type: 计算类型 (int8/float16/float32)
            use_china_mirror: 是否使用国内镜像
            auto_switch_mirror: 是否自动切换镜像源
            output_dir: 输出目录
            keep_audio: 是否保留音频文件
            language: 语言代码
            prefer_offline: 优先使用离线方式
        """
        self.cookie_file = cookie_file
        self.output_dir = Path(output_dir)
        self.keep_audio = keep_audio
        self.language = language
        self.prefer_offline = prefer_offline
        self.auto_switch_mirror = auto_switch_mirror
        
        # 自动检测系统资源并选择合适的模型
        if model_name is None or device is None:
            system_info = self._detect_system_resources()
            logger.info(f"系统资源检测结果：{system_info}")
            
            if model_name is None:
                model_name = system_info['recommended_model']
            if device is None:
                device = system_info['recommended_device']
        
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        
        # 镜像源列表
        self.mirrors = [
            ("原始源", "https://huggingface.co"),
            ("国内镜像", "https://hf-mirror.com"),
        ]
        
        # 设置初始镜像
        if use_china_mirror:
            os.environ['HF_ENDPOINT'] = self.mirrors[1][1]
            logger.info("使用国内镜像源：https://hf-mirror.com")
        
        # 初始化
        self.model = None
        self.credential = None
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BilibiliTranscriber 初始化完成")
        logger.info(f"模型：{model_name}, 设备：{device}, 语言：{language}")
        logger.info(f"自动切换镜像：{auto_switch_mirror}")
    
    def _detect_system_resources(self) -> Dict[str, Any]:
        """检测系统资源，推荐合适的模型"""
        import psutil
        
        # 获取 CPU 核心数
        cpu_count = psutil.cpu_count(logical=True)
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024 ** 3)
        
        # 检测 GPU
        has_cuda = False
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if has_cuda:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                logger.info(f"检测到 GPU: {gpu_name} ({gpu_memory:.1f} GB)")
        except:
            pass
        
        # 推荐模型策略
        if has_cuda:
            recommended_device = "cuda"
            recommended_model = "medium"  # GPU 可以使用更大的模型
        elif memory_gb >= 8:
            recommended_device = "cpu"
            recommended_model = "base"  # 8GB+ 内存可以使用 base
        elif memory_gb >= 4:
            recommended_device = "cpu"
            recommended_model = "tiny"  # 4-8GB 使用 tiny
        else:
            recommended_device = "cpu"
            recommended_model = "vosk"  # 内存不足时使用 Vosk
        
        return {
            "cpu_count": cpu_count,
            "memory_gb": round(memory_gb, 2),
            "has_cuda": has_cuda,
            "recommended_model": recommended_model,
            "recommended_device": recommended_device
        }
    
    def _load_cookie(self) -> Optional[str]:
        """加载 Cookie"""
        if not self.cookie_file:
            cookie = os.environ.get('BILIBILI_COOKIE')
            if cookie:
                logger.info("从环境变量加载 Cookie")
                return cookie
            
            default_paths = [
                "~/.bilibili_cookie.txt",
                "~/bilibili_cookie.txt",
                "./bilibili_cookie.txt"
            ]
            
            for path in default_paths:
                expanded_path = Path(path).expanduser()
                if expanded_path.exists():
                    self.cookie_file = str(expanded_path)
                    logger.info(f"找到 Cookie 文件：{self.cookie_file}")
                    break
        
        if self.cookie_file and Path(self.cookie_file).exists():
            try:
                with open(self.cookie_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"读取 Cookie 文件失败：{e}")
        
        logger.warning("未找到有效的 Cookie，部分功能可能受限")
        return None
    
    def _create_credential(self):
        """创建凭证"""
        from bilibili_api import Credential
        
        cookie_str = self._load_cookie()
        if not cookie_str:
            self.credential = None
            return
        
        try:
            cookies = {}
            for item in cookie_str.split('; '):
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k] = v
            
            credential = Credential(
                sessdata=cookies.get('SESSDATA', ''),
                bili_jct=cookies.get('bili_jct', ''),
                buvid3=cookies.get('buvid3', ''),
                dedeuserid=cookies.get('DedeUserID', '')
            )
            
            logger.info("凭证创建成功")
            self.credential = credential
            
        except Exception as e:
            logger.error(f"创建凭证失败：{e}")
            self.credential = None
    
    def get_video_info(self, bvid: str) -> Optional[VideoInfo]:
        """获取视频信息"""
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            info = sync(v.get_info())
            cid = sync(v.get_cid(page_index=1))
            
            video_info = VideoInfo(
                bvid=bvid,
                title=info.get('title', ''),
                duration=info.get('duration', 0),
                up_name=info.get('owner', {}).get('name', ''),
                up_mid=str(info.get('owner', {}).get('mid', '')),
                pubdate=info.get('pubdate', 0),
                cid=cid
            )
            
            logger.info(f"视频信息获取成功：{video_info.title}")
            return video_info
            
        except Exception as e:
            logger.error(f"获取视频信息失败：{e}")
            return None
    
    def try_get_cc_subtitle(self, bvid: str, cid: int) -> Optional[SubtitleResult]:
        """
        第一步：尝试获取 CC 字幕
        优先级最高，因为不需要下载和转录
        """
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            subtitle_info = sync(v.get_subtitle())
            
            subtitles = subtitle_info.get('subtitles', [])
            if not subtitles:
                logger.info("未找到 CC 字幕")
                return None
            
            logger.info(f"找到 {len(subtitles)} 个 CC 字幕轨道")
            
            # 优先选择中文字幕
            target_sub = None
            for sub in subtitles:
                if sub.get('lan') in ['zh-CN', 'zh']:
                    target_sub = sub
                    break
            
            if not target_sub:
                target_sub = subtitles[0]
            
            # 下载字幕
            subtitle_url = target_sub.get('subtitle_url', '')
            if not subtitle_url.startswith('http'):
                subtitle_url = f"https:{subtitle_url}"
            
            logger.info(f"下载 CC 字幕：{target_sub.get('lan')}")
            response = requests.get(subtitle_url, timeout=30)
            subtitle_data = response.json()
            
            # 转换为 TranscriptSegment 格式
            transcript = []
            for line in subtitle_data.get('body', []):
                transcript.append(TranscriptSegment(
                    start=line.get('from', 0),
                    end=line.get('to', 0),
                    text=line.get('content', ''),
                    confidence=1.0
                ))
            
            logger.info(f"✅ CC 字幕获取成功：{len(transcript)} 条")
            return SubtitleResult(
                success=True,
                source="cc",
                transcript=[{"start": s.start, "end": s.end, "text": s.text} for s in transcript]
            )
            
        except Exception as e:
            logger.warning(f"获取 CC 字幕失败：{e}")
            return None
    
    def try_get_ai_subtitle(self, bvid: str, cid: int) -> Optional[SubtitleResult]:
        """
        第二步：尝试获取 AI 字幕
        优先级次之，也不需要下载和转录
        """
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            
            # 尝试获取 AI 字幕
            subtitle_info = sync(v.get_subtitle())
            subtitles = subtitle_info.get('subtitles', [])
            
            # 查找 AI 字幕
            ai_subtitle = None
            for sub in subtitles:
                if sub.get('type') == 'ai' or sub.get('lan', '').startswith('ai-'):
                    ai_subtitle = sub
                    break
            
            if not ai_subtitle:
                logger.info("未找到 AI 字幕")
                return None
            
            # 下载 AI 字幕
            subtitle_url = ai_subtitle.get('subtitle_url', '')
            if not subtitle_url.startswith('http'):
                subtitle_url = f"https:{subtitle_url}"
            
            logger.info(f"下载 AI 字幕：{ai_subtitle.get('lan')}")
            response = requests.get(subtitle_url, timeout=30)
            subtitle_data = response.json()
            
            # 转换为 TranscriptSegment 格式
            transcript = []
            for line in subtitle_data.get('body', []):
                transcript.append(TranscriptSegment(
                    start=line.get('from', 0),
                    end=line.get('to', 0),
                    text=line.get('content', ''),
                    confidence=0.95  # AI 字幕置信度略低于 CC
                ))
            
            logger.info(f"✅ AI 字幕获取成功：{len(transcript)} 条")
            return SubtitleResult(
                success=True,
                source="ai",
                transcript=[{"start": s.start, "end": s.end, "text": s.text} for s in transcript]
            )
            
        except Exception as e:
            logger.warning(f"获取 AI 字幕失败：{e}")
            return None
    
    def download_audio(self, bvid: str, video_info: VideoInfo, output_path: Path) -> Optional[str]:
        """
        第三步：下载音频文件
        只有在没有字幕的情况下才需要
        """
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            urls = sync(v.get_download_url(page_index=0))
            
            audio_list = urls.get('dash', {}).get('audio', [])
            if not audio_list:
                logger.error("未找到音频 URL")
                return None
            
            audio_url = audio_list[0].get('baseUrl', '')
            if not audio_url:
                return None
            
            logger.info(f"音频 URL 获取成功")
            
            cookie_str = self._load_cookie()
            headers = {
                'Cookie': cookie_str if cookie_str else '',
                'User-Agent': 'Mozilla/5.0',
                'Referer': f'https://www.bilibili.com/video/{bvid}'
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"开始下载音频：{output_path}")
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = output_path.stat().st_size
            logger.info(f"音频下载完成：{file_size/1024/1024:.2f} MB")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"下载音频失败：{e}")
            return None
    
    def download_video(self, bvid: str, video_info: VideoInfo, output_path: Path) -> Optional[str]:
        """
        第四步：下载视频文件
        只有在无法获取音频时才需要（极少情况）
        """
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            urls = sync(v.get_download_url(page_index=0))
            
            # 获取视频 URL
            video_list = urls.get('dash', {}).get('video', [])
            if not video_list:
                logger.error("未找到视频 URL")
                return None
            
            # 选择合适清晰度的视频
            video_url = video_list[0].get('baseUrl', '')
            if not video_url:
                return None
            
            logger.info(f"视频 URL 获取成功")
            
            cookie_str = self._load_cookie()
            headers = {
                'Cookie': cookie_str if cookie_str else '',
                'User-Agent': 'Mozilla/5.0',
                'Referer': f'https://www.bilibili.com/video/{bvid}'
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"开始下载视频：{output_path}")
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = output_path.stat().st_size
            logger.info(f"视频下载完成：{file_size/1024/1024:.2f} MB")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"下载视频失败：{e}")
            return None
    
    def _load_model(self):
        """加载模型（Whisper 或 Vosk）"""
        if self.model is None:
            if self.model_name == "vosk":
                return self._load_vosk_model()
            else:
                if self.auto_switch_mirror:
                    self.model = self._load_model_with_retry()
                else:
                    self._load_model_simple()
    
    def _load_vosk_model(self):
        """加载 Vosk 离线模型"""
        try:
            from vosk import Model
            
            model_paths = [
                self.model_name if self.model_name != "vosk" else None,
                "/root/.cache/vosk/vosk-model-small-cn-0.22",
                "/usr/share/vosk-models/vosk-model-small-cn-0.22",
                Path.home() / ".cache/vosk/vosk-model-small-cn-0.22",
            ]
            
            model_path = None
            for path in [p for p in model_paths if p]:
                if Path(path).exists():
                    model_path = path
                    break
            
            if not model_path:
                raise FileNotFoundError("未找到 Vosk 模型")
            
            logger.info(f"加载 Vosk 模型：{model_path}")
            self.model = Model(str(model_path))
            logger.info(f"✅ Vosk 模型加载成功")
            return self.model
            
        except Exception as e:
            logger.error(f"Vosk 模型加载失败：{e}")
            raise
    
    def _load_model_simple(self):
        """简单加载 Whisper 模型"""
        logger.info(f"加载 Whisper {self.model_name} 模型...")
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info(f"模型加载成功：{self.model_name}")
        except Exception as e:
            logger.error(f"模型加载失败：{e}")
            raise
    
    def _load_model_with_retry(self):
        """加载模型，失败时自动切换镜像源"""
        from faster_whisper import WhisperModel
        
        last_error = None
        
        for name, mirror in self.mirrors:
            try:
                if mirror != "https://huggingface.co":
                    logger.info(f"🔄 切换到镜像源：{mirror} ({name})")
                    os.environ['HF_ENDPOINT'] = mirror
                else:
                    logger.info(f"尝试原始源：{mirror}")
                
                logger.info(f"加载 Whisper {self.model_name} 模型...")
                model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
                
                logger.info(f"✅ 模型加载成功：{self.model_name} (来源：{name})")
                return model
                
            except Exception as e:
                logger.warning(f"❌ 镜像源 {name} 失败：{e}")
                last_error = e
                continue
        
        error_msg = (
            f"所有镜像源都失败。最后错误：{last_error}\n"
            f"建议：\n"
            f"1. 检查网络连接\n"
            f"2. 使用 Vosk 离线引擎：设置 model_name='vosk'\n"
            f"3. 手动下载模型到本地"
        )
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def transcribe_audio(self, audio_path: str) -> Optional[List[TranscriptSegment]]:
        """转录音频"""
        try:
            self._load_model()
            
            logger.info(f"开始转录：{audio_path}")
            start_time = time.time()
            
            if self.model_name == "vosk":
                transcript = self._transcribe_with_vosk(audio_path)
            else:
                transcript = self._transcribe_with_whisper(audio_path)
            
            processing_time = time.time() - start_time
            logger.info(f"转录完成：{len(transcript)} 个片段，耗时：{processing_time:.2f}秒")
            
            return transcript
            
        except Exception as e:
            logger.error(f"转录失败：{e}")
            return None
    
    def _transcribe_with_whisper(self, audio_path: str) -> List[TranscriptSegment]:
        """使用 Whisper 转录"""
        segments, info = self.model.transcribe(
            audio_path,
            language=self.language,
            beam_size=5,
            best_of=5,
            word_timestamps=False,
            prepend_punctuations="\"'""¿([{-",
            append_punctuations="\"'.。,，!！?？:：")]}",
        )
        
        logger.info(f"语言检测：{info.language}, 置信度：{info.language_probability:.2f}")
        
        transcript = []
        for segment in segments:
            transcript.append(TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                confidence=getattr(segment, 'confidence', None)
            ))
        
        return transcript
    
    def _transcribe_with_vosk(self, audio_path: str) -> List[TranscriptSegment]:
        """使用 Vosk 转录"""
        import wave
        from vosk import KaldiRecognizer
        
        logger.info(f"使用 Vosk 引擎转录：{audio_path}")
        
        # 转换为 WAV
        wav_path = str(audio_path).replace('.m4a', '_temp.wav').replace('.mp4', '_temp.wav')
        if not Path(wav_path).exists():
            import subprocess
            subprocess.run([
                'ffmpeg', '-y', '-i', str(audio_path),
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                wav_path
            ], check=True, capture_output=True)
        
        transcript = []
        with wave.open(wav_path, "rb") as wf:
            rec = KaldiRecognizer(self.model, wf.getframerate())
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get('text'):
                        transcript.append(TranscriptSegment(
                            start=0,
                            end=0,
                            text=result['text']
                        ))
            
            final_result = json.loads(rec.FinalResult())
            if final_result.get('text'):
                transcript.append(TranscriptSegment(
                    start=0,
                    end=0,
                    text=final_result['text']
                ))
        
        # 清理临时文件
        try:
            Path(wav_path).unlink()
        except:
            pass
        
        return transcript
    
    def save_transcript(
        self,
        transcript: List[TranscriptSegment],
        video_info: VideoInfo,
        output_path: Path,
        format: str = "txt"
    ) -> bool:
        """保存转录结果"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "txt":
                lines = []
                for seg in transcript:
                    lines.append(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
            elif format == "json":
                data = {
                    "video_info": asdict(video_info),
                    "transcript": [asdict(seg) for seg in transcript],
                    "metadata": {
                        "model": self.model_name,
                        "language": self.language,
                        "processing_time": datetime.now().isoformat()
                    }
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format == "markdown":
                lines = [
                    f"# {video_info.title}",
                    "",
                    "**视频信息**",
                    f"- BV 号：{video_info.bvid}",
                    f"- 时长：{video_info.duration}秒",
                    f"- UP 主：{video_info.up_name}",
                    f"- 发布时间：{datetime.fromtimestamp(video_info.pubdate).strftime('%Y-%m-%d %H:%M:%S')}",
                    f"- 处理时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "**转录内容**",
                    ""
                ]
                
                for seg in transcript:
                    lines.append(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
            
            else:
                logger.error(f"不支持的格式：{format}")
                return False
            
            logger.info(f"转录结果保存成功：{output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存转录结果失败：{e}")
            return False
    
    def process(
        self,
        bvid: str,
        output_format: str = "txt",
        validate: bool = True
    ) -> ProcessingResult:
        """
        处理 B 站视频 - 优化优先级版本
        
        优先级：
        1. 获取 CC 字幕（最快，无需下载）
        2. 获取 AI 字幕（次快，无需下载）
        3. 下载音频并转录（需要下载）
        4. 下载视频并提取音频（最后选择，极少使用）
        
        Args:
            bvid: B 站视频 BV 号
            output_format: 输出格式 (txt/json/markdown)
            validate: 是否验证转录内容
        
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        warnings = []
        method_used = None
        
        try:
            logger.info(f"开始处理视频：{bvid}")
            logger.info("=" * 60)
            logger.info("处理策略：字幕优先 > AI 字幕 > 音频转录 > 视频下载")
            logger.info("=" * 60)
            
            # 获取视频信息
            video_info = self.get_video_info(bvid)
            if not video_info:
                return ProcessingResult(
                    success=False,
                    error="无法获取视频信息"
                )
            
            # 创建输出目录
            video_output_dir = self.output_dir / bvid
            video_output_dir.mkdir(parents=True, exist_ok=True)
            
            transcript = None
            
            # ========== 第一步：尝试获取 CC 字幕 ==========
            logger.info("\n【步骤 1/4】尝试获取 CC 字幕...")
            subtitle_result = self.try_get_cc_subtitle(bvid, video_info.cid)
            if subtitle_result and subtitle_result.success:
                logger.info("✅ 使用 CC 字幕（无需下载和转录）")
                method_used = "cc_subtitle"
                transcript = [
                    TranscriptSegment(
                        start=s.get('start', 0),
                        end=s.get('end', 0),
                        text=s.get('text', ''),
                        confidence=1.0
                    )
                    for s in subtitle_result.transcript
                ]
            
            # ========== 第二步：尝试获取 AI 字幕 ==========
            if not transcript:
                logger.info("\n【步骤 2/4】尝试获取 AI 字幕...")
                subtitle_result = self.try_get_ai_subtitle(bvid, video_info.cid)
                if subtitle_result and subtitle_result.success:
                    logger.info("✅ 使用 AI 字幕（无需下载和转录）")
                    method_used = "ai_subtitle"
                    transcript = [
                        TranscriptSegment(
                            start=s.get('start', 0),
                            end=s.get('end', 0),
                            text=s.get('text', ''),
                            confidence=0.95
                        )
                        for s in subtitle_result.transcript
                    ]
            
            # ========== 第三步：下载音频并转录 ==========
            if not transcript:
                logger.info("\n【步骤 3/4】下载音频并转录...")
                audio_path = video_output_dir / "audio.m4a"
                downloaded_path = self.download_audio(bvid, video_info, audio_path)
                
                if downloaded_path:
                    transcript = self.transcribe_audio(downloaded_path)
                    if transcript:
                        logger.info("✅ 使用音频转录")
                        method_used = "audio_transcribe"
            
            # ========== 第四步：下载视频并提取音频 ==========
            if not transcript:
                logger.info("\n【步骤 4/4】下载视频并提取音频（最后选择）...")
                video_path = video_output_dir / "video.mp4"
                downloaded_path = self.download_video(bvid, video_info, video_path)
                
                if downloaded_path:
                    # 从视频提取音频
                    audio_path = video_output_dir / "audio.m4a"
                    import subprocess
                    subprocess.run([
                        'ffmpeg', '-y', '-i', downloaded_path,
                        '-vn', '-acodec', 'copy',
                        str(audio_path)
                    ], check=True, capture_output=True)
                    
                    transcript = self.transcribe_audio(str(audio_path))
                    if transcript:
                        logger.info("✅ 使用视频提取音频转录")
                        method_used = "video_transcribe"
            
            # 检查是否成功获取转录
            if not transcript:
                return ProcessingResult(
                    success=False,
                    error="所有方法都失败：CC 字幕、AI 字幕、音频转录、视频转录"
                )
            
            # 验证转录内容
            if validate:
                transcript_text = " ".join([seg.text for seg in transcript])
                # 简单验证
                if len(transcript_text) < 50:
                    warnings.append(f"转录内容过短：{len(transcript_text)} 字")
            
            # 保存结果
            transcript_path = video_output_dir / f"transcript.{output_format}"
            if not self.save_transcript(transcript, video_info, transcript_path, output_format):
                return ProcessingResult(
                    success=False,
                    error="保存转录结果失败"
                )
            
            # 清理临时文件
            if not self.keep_audio:
                try:
                    audio_file = video_output_dir / "audio.m4a"
                    if audio_file.exists():
                        audio_file.unlink()
                    video_file = video_output_dir / "video.mp4"
                    if video_file.exists():
                        video_file.unlink()
                    logger.info("临时文件已清理")
                except Exception as e:
                    warnings.append(f"清理临时文件失败：{e}")
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                success=True,
                video_info=video_info,
                transcript=transcript,
                audio_path=str(audio_path) if self.keep_audio and method_used in ["audio_transcribe", "video_transcribe"] else None,
                transcript_path=str(transcript_path),
                processing_time=processing_time,
                warnings=warnings if warnings else None,
                method_used=method_used
            )
            
            logger.info("\n" + "=" * 60)
            logger.info(f"✅ 视频处理完成：{bvid}")
            logger.info(f"使用方法：{method_used}")
            logger.info(f"总耗时：{processing_time:.2f}秒")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"处理视频时发生错误：{e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class BilibiliLogin:
    """B 站扫码登录工具"""
    
    def __init__(self):
        self.qrcode_key = None
        self.qrcode_url = None
    
    def generate_qr(self) -> str:
        """生成登录二维码"""
        import qrcode
        
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get('code') == 0:
            self.qrcode_key = data['data']['qrcode_key']
            self.qrcode_url = data['data']['url']
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.qrcode_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            qr_path = "/tmp/bilibili_login_qr.png"
            img.save(qr_path)
            
            logger.info(f"二维码已生成：{qr_path}")
            return self.qrcode_url
        else:
            raise Exception(f"生成二维码失败：{data}")
    
    def poll(self) -> Dict[str, Any]:
        """轮询登录状态"""
        if not self.qrcode_key:
            raise Exception("请先生成二维码")
        
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qrcode_key}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get('code') == 0:
            result = data['data']
            
            if 'url' in result:
                import urllib.parse
                parsed = urllib.parse.urlparse(result['url'])
                params = urllib.parse.parse_qs(parsed.query)
                
                cookie = {
                    'SESSDATA': params.get('SESSDATA', [''])[0],
                    'bili_jct': params.get('bili_jct', [''])[0],
                    'DedeUserID': params.get('DedeUserID', [''])[0],
                }
                
                from bilibili_api import Credential, user, sync
                credential = Credential(
                    sessdata=cookie['SESSDATA'],
                    bili_jct=cookie['bili_jct'],
                    dedeuserid=cookie['DedeUserID']
                )
                
                u = user.User(credential=credential)
                user_info = sync(u.get_user_info())
                
                return {
                    'success': True,
                    'username': user_info.get('name', 'Unknown'),
                    'is_vip': user_info.get('vipStatus', 0) == 1,
                    'cookie': f"SESSDATA={cookie['SESSDATA']}; bili_jct={cookie['bili_jct']}; DedeUserID={cookie['DedeUserID']}"
                }
        
        return {'success': False}


if __name__ == "__main__":
    print("B 站视频转录专家 v2.0 - 优化优先级版本")
    print("=" * 60)
    print("处理策略：字幕优先 > AI 字幕 > 音频转录 > 视频下载")
    print("=" * 60)
    
    # 示例：自动检测系统资源
    transcriber = BilibiliTranscriber(
        cookie_file="~/.bilibili_cookie.txt",
        model_name=None,  # 自动选择
        device=None  # 自动选择
    )
