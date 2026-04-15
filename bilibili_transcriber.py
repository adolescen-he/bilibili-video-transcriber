#!/usr/bin/env python3
"""
B站视频转录专家 - 核心处理模块
专业处理B站视频字幕问题，支持语音转文字、字幕下载、内容分析
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
from bilibili_api import video, sync, Credential
from faster_whisper import WhisperModel
from pydub import AudioSegment

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
    """B站视频转录器"""
    
    def __init__(
        self,
        cookie_file: Optional[str] = None,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        use_china_mirror: bool = True,
        output_dir: str = "./bilibili_transcripts",
        keep_audio: bool = True,
        language: str = "zh"
    ):
        """
        初始化转录器
        
        Args:
            cookie_file: B站Cookie文件路径
            model_name: Whisper模型名称 (base/small/medium)
            device: 设备 (cpu/cuda)
            compute_type: 计算类型 (int8/float16/float32)
            use_china_mirror: 是否使用国内镜像
            output_dir: 输出目录
            keep_audio: 是否保留音频文件
            language: 语言代码
        """
        self.cookie_file = cookie_file
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.output_dir = Path(output_dir)
        self.keep_audio = keep_audio
        self.language = language
        
        # 设置国内镜像
        if use_china_mirror:
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            logger.info("使用国内镜像源: https://hf-mirror.com")
        
        # 初始化模型（懒加载）
        self.model = None
        self.credential = None
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BilibiliTranscriber 初始化完成")
        logger.info(f"模型: {model_name}, 设备: {device}, 语言: {language}")
    
    def _load_cookie(self) -> Optional[str]:
        """加载Cookie"""
        if not self.cookie_file:
            # 尝试从环境变量获取
            cookie = os.environ.get('BILIBILI_COOKIE')
            if cookie:
                logger.info("从环境变量加载Cookie")
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
                    logger.info(f"找到Cookie文件: {self.cookie_file}")
                    break
        
        if self.cookie_file and Path(self.cookie_file).exists():
            try:
                with open(self.cookie_file, 'r') as f:
                    cookie = f.read().strip()
                logger.info(f"从文件加载Cookie: {self.cookie_file}")
                return cookie
            except Exception as e:
                logger.warning(f"读取Cookie文件失败: {e}")
        
        logger.warning("未找到有效的Cookie，部分功能可能受限")
        return None
    
    def _create_credential(self) -> Optional[Credential]:
        """创建凭证"""
        cookie_str = self._load_cookie()
        if not cookie_str:
            return None
        
        try:
            # 解析Cookie
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
            return credential
            
        except Exception as e:
            logger.error(f"创建凭证失败: {e}")
            return None
    
    def _load_model(self):
        """加载Whisper模型"""
        if self.model is None:
            logger.info(f"加载Whisper {self.model_name} 模型...")
            try:
                self.model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info(f"模型加载成功: {self.model_name}")
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                raise
    
    def get_video_info(self, bvid: str) -> Optional[VideoInfo]:
        """获取视频信息"""
        try:
            if self.credential is None:
                self.credential = self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            info = sync(v.get_info())
            
            # 获取CID
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
            
            logger.info(f"视频信息获取成功: {video_info.title}")
            return video_info
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None
    
    def download_audio(self, bvid: str, video_info: VideoInfo, output_path: Path) -> Optional[str]:
        """下载音频文件"""
        try:
            if self.credential is None:
                self.credential = self._create_credential()
            
            v = video.Video(bvid=bvid, credential=self.credential)
            urls = sync(v.get_download_url(page_index=0))
            
            # 获取音频URL
            audio_list = urls.get('dash', {}).get('audio', [])
            if not audio_list:
                logger.error("未找到音频URL")
                return None
            
            # 选择最高质量的音频
            audio_info = audio_list[0]
            audio_url = audio_info.get('baseUrl', '')
            if not audio_url:
                logger.error("音频URL为空")
                return None
            
            logger.info(f"音频URL获取成功: {audio_url[:50]}...")
            
            # 下载音频
            cookie_str = self._load_cookie()
            headers = {
                'Cookie': cookie_str if cookie_str else '',
                'User-Agent': 'Mozilla/5.0',
                'Referer': f'https://www.bilibili.com/video/{bvid}'
            }
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"开始下载音频: {output_path}")
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
            logger.info(f"音频下载完成: {file_size/1024/1024:.2f} MB")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            return None
    
    def transcribe_audio(self, audio_path: str) -> Optional[List[TranscriptSegment]]:
        """转录音频"""
        try:
            self._load_model()
            
            logger.info(f"开始转录: {audio_path}")
            start_time = time.time()
            
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
                prepend_punctuations="\"'“¿([{-",
                append_punctuations="\"'.。,，!！?？:：”)]}、"
            )
            
            logger.info(f"语言检测: {info.language}, 置信度: {info.language_probability:.2f}")
            
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
            
            processing_time = time.time() - start_time
            logger.info(f"转录完成: {len(transcript)} 个片段, 耗时: {processing_time:.2f}秒")
            
            return transcript
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            return None
    
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
                # JSON格式
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
                # Markdown格式
                lines = [
                    f"# {video_info.title}",
                    "",
                    "**视频信息**",
                    f"- BV号: {video_info.bvid}",
                    f"- 时长: {video_info.duration}秒",
                    f"- UP主: {video_info.up_name}",
                    f"- 发布时间: {datetime.fromtimestamp(video_info.pubdate).strftime('%Y-%m-%d %H:%M:%S')}",
                    f"- 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "**转录内容**",
                    ""
                ]
                
                for seg in transcript:
                    lines.append(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
            
            else:
                logger.error(f"不支持的格式: {format}")
                return False
            
            logger.info(f"转录结果保存成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存转录结果失败: {e}")
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
            "is_valid": match_rate > 0.3,  # 30%匹配度阈值
            "keywords_found": match_count,
            "total_keywords": len(keywords),
            "keywords": keywords
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本提取关键词"""
        # 简单的关键词提取
        import re
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分割单词
        words = text.split()
        # 过滤短词和常见词
        common_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [word for word in words if len(word) > 1 and word not in common_words]
        return keywords[:10]  # 返回前10个关键词
    
    def process(
        self,
        bvid: str,
        output_format: str = "txt",
        validate: bool = True
    ) -> ProcessingResult:
        """
        处理B站视频
        
        Args:
            bvid: B站视频BV号
            output_format: 输出格式 (txt/json/markdown)
            validate: 是否验证转录内容
        
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        warnings = []
        
        try:
            logger.info(f"开始处理视频: {bvid}")
            
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
                    warnings.append(f"转录内容验证失败: 匹配度 {validation_result['match_rate']:.1%}")
                    logger.warning(f"转录内容可能有问题: 匹配度 {validation_result['match_rate']:.1%}")
                else:
                    logger.info(f"转录内容验证通过: 匹配度 {validation_result['match_rate']:.1%}")
            
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
                    warnings.append(f"清理音频文件失败: {e}")
            
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
            
            logger.info(f"视频处理完成: {bvid}, 耗时: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f