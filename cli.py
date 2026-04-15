#!/usr/bin/env python3
"""
B站视频转录专家 - 命令行工具
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Optional

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from bilibili_transcriber import BilibiliTranscriber, ProcessingResult

def setup_logging(verbose: bool = False, debug: bool = False):
    """设置日志"""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bilibili_transcriber.log')
        ]
    )

def print_result(result: ProcessingResult, show_transcript: bool = False):
    """打印处理结果"""
    if result.success:
        print("\n" + "="*60)
        print("✅ 处理成功！")
        print("="*60)
        
        if result.video_info:
            print(f"📺 视频标题: {result.video_info.title}")
            print(f"🔗 BV号: {result.video_info.bvid}")
            print(f"⏱️ 时长: {result.video_info.duration}秒")
            print(f"👤 UP主: {result.video_info.up_name}")
        
        if result.transcript_path:
            print(f"📄 转录文件: {result.transcript_path}")
        
        if result.audio_path:
            print(f"🎵 音频文件: {result.audio_path}")
        
        if result.processing_time:
            print(f"⏰ 处理时间: {result.processing_time:.2f}秒")
        
        if result.transcript and show_transcript:
            print("\n📝 转录内容（前5段）:")
            for i, seg in enumerate(result.transcript[:5]):
                print(f"  [{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
            
            if len(result.transcript) > 5:
                print(f"  ... 还有 {len(result.transcript) - 5} 段")
        
        if result.warnings:
            print("\n⚠️ 警告:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        print("="*60)
        
    else:
        print("\n" + "="*60)
        print("❌ 处理失败！")
        print("="*60)
        print(f"错误: {result.error}")
        print("="*60)

def process_single(
    bvid: str,
    cookie_file: Optional[str],
    model: str,
    output_dir: str,
    output_format: str,
    keep_audio: bool,
    verbose: bool,
    debug: bool
) -> bool:
    """处理单个视频"""
    try:
        # 初始化转录器
        transcriber = BilibiliTranscriber(
            cookie_file=cookie_file,
            model_name=model,
            output_dir=output_dir,
            keep_audio=keep_audio
        )
        
        # 处理视频
        result = transcriber.process(
            bvid=bvid,
            output_format=output_format,
            validate=True
        )
        
        # 打印结果
        print_result(result, show_transcript=verbose)
        
        return result.success
        
    except Exception as e:
        logging.error(f"处理失败: {e}")
        print(f"\n❌ 处理失败: {e}")
        return False

def process_batch(
    bvid_file: str,
    cookie_file: Optional[str],
    model: str,
    output_dir: str,
    output_format: str,
    keep_audio: bool,
    parallel: int,
    verbose: bool,
    debug: bool
) -> bool:
    """批量处理视频"""
    try:
        # 读取BV号列表
        with open(bvid_file, 'r') as f:
            lines = f.readlines()
        
        bvids = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 提取BV号
                if 'BV' in line:
                    # 从URL中提取BV号
                    import re
                    match = re.search(r'BV[0-9A-Za-z]{10}', line)
                    if match:
                        bvids.append(match.group(0))
                    else:
                        bvids.append(line)
                else:
                    bvids.append(line)
        
        if not bvids:
            print("❌ 未找到有效的BV号")
            return False
        
        print(f"📋 找到 {len(bvids)} 个视频需要处理")
        
        # 初始化转录器
        transcriber = BilibiliTranscriber(
            cookie_file=cookie_file,
            model_name=model,
            output_dir=output_dir,
            keep_audio=keep_audio
        )
        
        success_count = 0
        fail_count = 0
        
        # 顺序处理
        for i, bvid in enumerate(bvids, 1):
            print(f"\n📊 处理进度: {i}/{len(bvids)} ({bvid})")
            
            try:
                result = transcriber.process(
                    bvid=bvid,
                    output_format=output_format,
                    validate=True
                )
                
                if result.success:
                    success_count += 1
                    print(f"✅ 成功: {bvid}")
                else:
                    fail_count += 1
                    print(f"❌ 失败: {bvid} - {result.error}")
                    
            except Exception as e:
                fail_count += 1
                print(f"❌ 异常: {bvid} - {e}")
        
        # 打印统计
        print("\n" + "="*60)
        print("📊 批量处理完成")
        print("="*60)
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {fail_count}")
        print(f"📈 成功率: {success_count/len(bvids)*100:.1f}%")
        print("="*60)
        
        return fail_count == 0
        
    except Exception as e:
        logging.error(f"批量处理失败: {e}")
        print(f"\n❌ 批量处理失败: {e}")
        return False

def check_cookie(cookie_file: Optional[str]) -> bool:
    """检查Cookie状态"""
    try:
        from bilibili_api import sync, Credential
        
        # 尝试加载Cookie
        if cookie_file and Path(cookie_file).exists():
            with open(cookie_file, 'r') as f:
                cookie_str = f.read().strip()
            
            # 解析Cookie
            cookies = {}
            for item in cookie_str.split('; '):
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k] = v
            
            # 创建凭证
            credential = Credential(
                sessdata=cookies.get('SESSDATA', ''),
                bili_jct=cookies.get('bili_jct', ''),
                buvid3=cookies.get('buvid3', ''),
                dedeuserid=cookies.get('DedeUserID', '')
            )
            
            # 测试凭证
            from bilibili_api import user
            u = user.User(credential=credential)
            info = sync(u.get_user_info())
            
            print("✅ Cookie有效")
            print(f"👤 用户: {info.get('name', '未知')}")
            print(f"📧 邮箱: {info.get('email', '未设置')}")
            print(f"📱 手机: {info.get('mobile', '未设置')}")
            
            return True
            
        else:
            print("❌ Cookie文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ Cookie检查失败: {e}")
        return False

def update_cookie(cookie_file: str, cookie_str: str) -> bool:
    """更新Cookie"""
    try:
        # 确保目录存在
        Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 保存Cookie
        with open(cookie_file, 'w') as f:
            f.write(cookie_str.strip())
        
        print(f"✅ Cookie已更新: {cookie_file}")
        
        # 验证Cookie
        return check_cookie(cookie_file)
        
    except Exception as e:
        print(f"❌ 更新Cookie失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='B站视频转录专家 - 专业处理B站视频字幕问题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理单个视频
  %(prog)s BV1txQGByERW
  
  # 指定Cookie文件
  %(prog)s BV1txQGByERW --cookie ~/.bilibili_cookie.txt
  
  # 使用medium模型
  %(prog)s BV1txQGByERW --model medium
  
  # 批量处理
  %(prog)s --batch bv_list.txt --parallel 3
  
  # 检查Cookie状态
  %(prog)s --check-cookie
  
  # 更新Cookie
  %(prog)s --update-cookie "SESSDATA=xxx; bili_jct=xxx"
        """
    )
    
    # 视频参数
    video_group = parser.add_mutually_exclusive_group(required=True)
    video_group.add_argument(
        'bvid',
        nargs='?',
        help='B站视频BV号'
    )
    video_group.add_argument(
        '--batch',
        metavar='FILE',
        help='批量处理，指定包含BV号列表的文件'
    )
    
    # 功能参数
    parser.add_argument(
        '--check-cookie',
        action='store_true',
        help='检查Cookie状态'
    )
    parser.add_argument(
        '--update-cookie',
        metavar='COOKIE_STRING',
        help='更新Cookie'
    )
    
    # 配置参数
    parser.add_argument(
        '--cookie',
        metavar='FILE',
        help='Cookie文件路径（默认: ~/.bilibili_cookie.txt）'
    )
    parser.add_argument(
        '--model',
        choices=['base', 'small', 'medium'],
        default='base',
        help='Whisper模型（默认: base）'
    )
    parser.add_argument(
        '--output',
        metavar='DIR',
        default='./bilibili_transcripts',
        help='输出目录（默认: ./bilibili_transcripts）'
    )
    parser.add_argument(
        '--format',
        choices=['txt', 'json', 'markdown'],
        default='txt',
        help='输出格式（默认: txt）'
    )
    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='保留音频文件'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='并行处理数量（默认: 1）'
    )
    
    # 调试参数
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='调试模式'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='B站视频转录专家 v1.0.0'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.verbose, args.debug)
    
    # 处理不同模式
    try:
        if args.check_cookie:
            # 检查Cookie模式
            cookie_file = args.cookie or "~/.bilibili_cookie.txt"
            success = check_cookie(cookie_file)
            sys.exit(0 if success else 1)
        
        elif args.update_cookie:
            # 更新Cookie模式
            cookie_file = args.cookie or "~/.bilibili_cookie.txt"
            success = update_cookie(cookie_file, args.update_cookie)
            sys.exit(0 if success else 1)
        
        elif args.batch:
            # 批量处理模式
            success = process_batch(
                bvid_file=args.batch,
                cookie_file=args.cookie,
                model=args.model,
                output_dir=args.output,
                output_format=args.format,
                keep_audio=args.keep_audio,
                parallel=args.parallel,
                verbose=args.verbose,
                debug=args.debug
            )
            sys.exit(0 if success else 1)
        
        else:
            # 单个视频处理模式
            success = process_single(
                bvid=args.bvid,
                cookie_file=args.cookie,
                model=args.model,
                output_dir=args.output,
                output_format=args.format,
                keep_audio=args.keep_audio,
                verbose=args.verbose,
                debug=args.debug
            )
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()