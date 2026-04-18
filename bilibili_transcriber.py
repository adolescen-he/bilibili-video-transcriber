#!/usr/bin/env python3
"""
B 站视频转录专家 - 核心处理模块
专业处理 B 站视频字幕问题，支持语音转文字、字幕下载、内容分析

更新日志：
- 2026-04-19: 添加镜像源自动切换功能
- 2026-04-19: 添加 Vosk 离线引擎支持
- 2026-04-19: 优化错误处理和重试机制
"""

import os
import sys
import json
import time
import logging
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


class BilibiliTranscriber:
    """B 站视频转录器"""
    
    def __init__(
        self,
        cookie_file: Optional[str] = None,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        use_china_mirror: bool = True,
        auto_switch_mirror: bool = True,
        output_dir: str = "./bilibili_transcripts",
        keep_audio: bool = True,
        language: str = "zh",
        engine: str = "whisper"  # whisper 或 vosk
    ):
        """
        初始化转录器
        
        Args:
            cookie_file: B 站 Cookie 文件路径
            model_name: Whisper 模型名称 (base/small/medium) 或 Vosk 模型路径
            device: 设备 (cpu/cuda)
            compute_type: 计算类型 (int8/float16/float32)
            use_china_mirror: 是否使用国内镜像
            auto_switch_mirror: 是否自动切换镜像源（失败时重试）
            output_dir: 输出目录
            keep_audio: 是否保留音频文件
            language: 语言代码
            engine: 转录引擎 (whisper/vosk)
        """
        self.cookie_file = cookie_file
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.output_dir = Path(output_dir)
        self.keep_audio = keep_audio
        self.language = language
        self.engine = engine
        self.auto_switch_mirror = auto_switch_mirror
        
        # 镜像源列表
        self.mirrors = [
            ("原始源", "https://huggingface.co"),
            ("国内镜像", "https://hf-mirror.com"),
        ]
        
        # 设置初始镜像
        if use_china_mirror:
            os.environ['HF_ENDPOINT'] = self.mirrors[1][1]
            logger.info("使用国内镜像源：https://hf-mirror.com")
        
        # 初始化模型（懒加载）
        self.model = None
        self.credential = None
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BilibiliTranscriber 初始化完成")
        logger.info(f"引擎：{engine}, 模型：{model_name}, 设备：{device}, 语言：{language}")
        logger.info(f"自动切换镜像：{auto_switch_mirror}")
    
    def _load_cookie(self) -> Optional[str]:
        """加载 Cookie"""
        if not self.cookie_file:
            # 尝试从环境变量获取
            cookie = os.environ.get('BILIBILI_COOKIE')
            if cookie:
                logger.info("从环境变量加载 Cookie")
                return cookie
            
            # 尝试默认位置
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
                    cookie = f.read().strip()
                logger.info(f"从文件加载 Cookie: {self.cookie_file}")
                return cookie
            except Exception as e:
                logger.warning(f"读取 Cookie 文件失败：{e}")
        
        logger.warning("未找到有效的 Cookie，部分功能可能受限")
        return None
    
    def _load_model(self):
        """加载模型（Whisper 或 Vosk）"""
        if self.model is None:
            if self.engine == "vosk":
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
            
            # 查找 Vosk 模型
            model_paths = [
                self.model_name,  # 自定义路径
                "/root/.cache/vosk/vosk-model-small-cn-0.22",
                "/usr/share/vosk-models/vosk-model-small-cn-0.22",
                Path.home() / ".cache/vosk/vosk-model-small-cn-0.22",
            ]
            
            model_path = None
            for path in model_paths:
                if Path(path).exists():
                    model_path = path
                    break
            
            if not model_path:
                raise FileNotFoundError(
                    "未找到 Vosk 模型，请确保已下载：\n"
                    "wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip\n"
                    "unzip vosk-model-small-cn-0.22.zip -d ~/.cache/vosk/"
                )
            
            logger.info(f"加载 Vosk 模型：{model_path}")
            self.model = Model(str(model_path))
            logger.info(f"✅ Vosk 模型加载成功")
            return self.model
            
        except Exception as e:
            logger.error(f"Vosk 模型加载失败：{e}")
            raise
    
    def _load_model_simple(self):
        """简单加载 Whisper 模型（不重试）"""
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
        
        # 所有镜像源都失败
        error_msg = (
            f"所有镜像源都失败。最后错误：{last_error}\n"
            f"建议：\n"
            f"1. 检查网络连接\n"
            f"2. 使用 Vosk 离线引擎：--engine vosk\n"
            f"3. 手动下载模型到本地"
        )
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_video_info(self, bvid: str) -> Optional[VideoInfo]:
        """获取视频信息"""
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            info = sync(v.get_info())
            
            # 获取 CID
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
    
    def _create_credential(self):
        """创建凭证"""
        from bilibili_api import Credential
        
        cookie_str = self._load_cookie()
        if not cookie_str:
            self.credential = None
            return
        
        try:
            # 解析 Cookie
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
    
    def download_audio(self, bvid: str, video_info: VideoInfo, output_path: Path) -> Optional[str]:
        """下载音频文件"""
        try:
            from bilibili_api import video, sync
            
            if self.credential is None:
                self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            urls = sync(v.get_download_url(page_index=0))
            
            # 获取音频 URL
            audio_list = urls.get('dash', {}).get('audio', [])
            if not audio_list:
                logger.error("未找到音频 URL")
                return None
            
            # 选择最高质量的音频
            audio_info = audio_list[0]
            audio_url = audio_info.get('baseUrl', '')
            if not audio_url:
                logger.error("音频 URL 为空")
                return None
            
            logger.info(f"音频 URL 获取成功：{audio_url[:50]}...")
            
            # 下载音频
            cookie_str = self._load_cookie()
            headers = {
                'Cookie': cookie_str if cookie_str else '',
                'User-Agent': 'Mozilla/5.0',
                'Referer': f'https://www.bilibili.com/video/{bvid}'
            }
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"开始下载音频：{output_path}")
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)
            
            file_size = output_path.stat().st_size
            logger.info(f"音频下载完成：{file_size/1024/1024:.2f} MB")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"下载音频失败：{e}")
            return None
    
    def transcribe_audio(self, audio_path: str) -> Optional[List[TranscriptSegment]]:
        """转录音频"""
        try:
            self._load_model()
            
            logger.info(f"开始转录：{audio_path}")
            start_time = time.time()
            
            if self.engine == "vosk":
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
            patience=1.0,
            length_penalty=1.0,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            condition_on_previous_text=True,
            initial_prompt=None,
            word_timestamps=False,
            prepend_punctuations="\"'""¿([{-",
            append_punctuations="\"'.。,，!！?？:：")]}",
        )
        
        logger.info(f"语言检测：{info.language}, 置信度：{info.language_probability:.2f}")
        
        # 收集转录结果
        transcript = []
        for segment in segments:
            transcript_segment = TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                confidence=getattr(segment, 'confidence', None)
            )
            transcript.append(transcript_segment)
        
        return transcript
    
    def _transcribe_with_vosk(self, audio_path: str) -> List[TranscriptSegment]:
        """使用 Vosk 转录"""
        import wave
        from vosk import KaldiRecognizer
        
        logger.info(f"使用 Vosk 引擎转录：{audio_path}")
        
        # 使用 ffmpeg 转换为 WAV（如果必要）
        wav_path = audio_path.replace('.m4a', '_temp.wav').replace('.mp4', '_temp.wav')
        if not Path(wav_path).exists():
            import subprocess
            subprocess.run([
                'ffmpeg', '-y', '-i', audio_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                wav_path
            ], check=True, capture_output=True)
        
        # 转录
        transcript = []
        with wave.open(wav_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                logger.error("音频格式错误")
                return []
            
            rec = KaldiRecognizer(self.model, wf.getframerate())
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get('text'):
                        transcript.append(TranscriptSegment(
                            start=0,  # Vosk 不提供精确时间戳
                            end=0,
                            text=result['text']
                        ))
            
            # 最终结果
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
                # 文本格式
                lines = []
                for seg in transcript:
                    lines.append(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
            elif format == "json":
                # JSON 格式
                data = {
                    "video_info": asdict(video_info),
                    "transcript": [asdict(seg) for seg in transcript],
                    "metadata": {
                        "model": self.model_name,
                        "engine": self.engine,
                        "language": self.language,
                        "processing_time": datetime.now().isoformat()
                    }
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format == "markdown":
                # Markdown 格式
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
    
    def validate_transcript(
        self,
        transcript_text: str,
        video_title: str,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """验证转录内容"""
        if keywords is None:
            # 从标题提取关键词
            keywords = self._extract_keywords(video_title)
        
        match_count = 0
        for keyword in keywords:
            if keyword.lower() in transcript_text.lower():
                match_count += 1
        
        match_rate = match_count / len(keywords) if keywords else 0
        
        return {
            "match_rate": match_rate,
            "is_valid": match_rate > 0.3,  # 30% 匹配度阈值
            "keywords_found": match_count,
            "total_keywords": len(keywords),
            "keywords": keywords
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本提取关键词"""
        import re
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分割单词
        words = text.split()
        # 过滤短词和常见词
        common_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [word for word in words if len(word) > 1 and word not in common_words]
        return keywords[:10]  # 返回前 10 个关键词
    
    def process(
        self,
        bvid: str,
        output_format: str = "txt",
        validate: bool = True
    ) -> ProcessingResult:
        """
        处理 B 站视频
        
        Args:
            bvid: B 站视频 BV 号
            output_format: 输出格式 (txt/json/markdown)
            validate: 是否验证转录内容
        
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        warnings = []
        
        try:
            logger.info(f"开始处理视频：{bvid}")
            
            # 1. 获取视频信息
            video_info = self.get_video_info(bvid)
            if not video_info:
                return ProcessingResult(
                    success=False,
                    error="无法获取视频信息"
                )
            
            # 2. 创建输出目录
            video_output_dir = self.output_dir / bvid
            video_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 3. 下载音频
            audio_path = video_output_dir / "audio.m4a"
            downloaded_path = self.download_audio(bvid, video_info, audio_path)
            if not downloaded_path:
                return ProcessingResult(
                    success=False,
                    error="下载音频失败"
                )
            
            # 4. 转录音频
            transcript = self.transcribe_audio(downloaded_path)
            if not transcript:
                return ProcessingResult(
                    success=False,
                    error="转录失败"
                )
            
            # 5. 验证转录内容
            if validate:
                transcript_text = " ".join([seg.text for seg in transcript])
                validation_result = self.validate_transcript(transcript_text, video_info.title)
                
                if not validation_result["is_valid"]:
                    warnings.append(f"转录内容验证失败：匹配度 {validation_result['match_rate']:.1%}")
                    logger.warning(f"转录内容可能有问题：匹配度 {validation_result['match_rate']:.1%}")
                else:
                    logger.info(f"转录内容验证通过：匹配度 {validation_result['match_rate']:.1%}")
            
            # 6. 保存结果
            transcript_path = video_output_dir / f"transcript.{output_format}"
            if not self.save_transcript(transcript, video_info, transcript_path, output_format):
                return ProcessingResult(
                    success=False,
                    error="保存转录结果失败"
                )
            
            # 7. 清理音频文件（如果不需要保留）
            if not self.keep_audio:
                try:
                    audio_path.unlink()
                    logger.info("音频文件已清理")
                except Exception as e:
                    warnings.append(f"清理音频文件失败：{e}")
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                success=True,
                video_info=video_info,
                transcript=transcript,
                audio_path=str(downloaded_path) if self.keep_audio else None,
                transcript_path=str(transcript_path),
                processing_time=processing_time,
                warnings=warnings if warnings else None
            )
            
            logger.info(f"视频处理完成：{bvid}, 耗时：{processing_time:.2f}秒")
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
            
            # 生成二维码图片
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
            
            # 提取 Cookie
            if 'url' in result:
                # 从 URL 中提取 Cookie
                import urllib.parse
                parsed = urllib.parse.urlparse(result['url'])
                params = urllib.parse.parse_qs(parsed.query)
                
                cookie = {
                    'SESSDATA': params.get('SESSDATA', [''])[0],
                    'bili_jct': params.get('bili_jct', [''])[0],
                    'DedeUserID': params.get('DedeUserID', [''])[0],
                }
                
                # 验证登录状态
                from bilibili_api import Credential
                credential = Credential(
                    sessdata=cookie['SESSDATA'],
                    bili_jct=cookie['bili_jct'],
                    dedeuserid=cookie['DedeUserID']
                )
                
                # 获取用户信息
                from bilibili_api import user
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
    # 测试代码
    print("B 站视频转录专家 - 测试模式")
    
    # 测试登录
    # login = BilibiliLogin()
    # qr_url = login.generate_qr()
    # print(f"请用 B 站 APP 扫码：{qr_url}")
    
    # 测试转录
    # transcriber = BilibiliTranscriber(
    #     cookie_file="~/.bilibili_cookie.txt",
    #     engine="vosk"  # 使用离线引擎
    # )
    # result = transcriber.process("BV1E7wtzaEdq")
    # print(f"处理结果：{result}")
