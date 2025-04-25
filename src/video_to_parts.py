import os
import re
#from moviepy.editor import VideoFileClip #新版本moviepy移除了editor
from moviepy.video.io.VideoFileClip import VideoFileClip
#from moviepy.Clip.Clip import subclip
from pathlib import Path

def parse_time(time_str):
    """解析包含冒号或小数点的时间字符串为秒数"""
    time_str = time_str.replace(',', '.')  # 兼容逗号分隔
    if ':' in time_str:
        parts = [float(x) for x in time_str.split(':')]
        if len(parts) == 2:    # MM:SS.ss 格式
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # HH:MM:SS.ss 格式
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(time_str)     # 直接秒数格式

def split_video(srt_path, video_path, progress_bar=None, status_text=None):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if status_text:
        status_text.text("正在解析字幕文件...")
    
    # 修正后的正则表达式（支持多种时间格式）
    pattern = r'([\d:.]+)\s*-\s*([\d:.]+)'
    time_blocks = re.findall(pattern, content)
    total_clips = len(time_blocks)
    
    if status_text:
        status_text.text(f"找到 {total_clips} 个视频片段，准备开始分割...")
    
    video = VideoFileClip(video_path)
    video_path = Path(video_path)
    output_dir = video_path.parent / f"{video_path.stem}_clips"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    video_segments = []
    for i, (start_str, end_str) in enumerate(time_blocks, 1):
        try:
            if status_text:
                status_text.text(f"正在处理片段 {i}/{total_clips}...")
            
            start = parse_time(start_str)
            end = parse_time(end_str)
            
            safe_start = start_str.replace(':', '_').replace('.', '_')
            safe_end = end_str.replace(':', '_').replace('.', '_')
            output_path = os.path.join(output_dir, f"clip_{i}_{safe_start}-{safe_end}.mp4")
            start = max(0, start-1)
            end = min(end+1, video.duration)
            video.subclipped(start, end).write_videofile(
                output_path, codec="libx264", audio_codec="aac")
            
            video_segments.append(str(output_path))
            
            # 更新进度条
            if progress_bar:
                progress = int (((i / total_clips) * 100)/5+60)
                progress_bar.progress(progress)
                
        except Exception as e:
            error_msg = f"处理片段 {i} 时出错: {str(e)}"
            if status_text:
                status_text.text(error_msg)
            print(error_msg)

    video.close()
    
    if status_text:
        status_text.text("视频分割完成！")
    if progress_bar:
        progress_bar.progress(80)
    
    return video_segments


# if __name__ == "__main__":
#     srt_file = r"D:\study life\university\competition\competition\2025_CS_application_ability_competition\AI\dat\chosen_result.txt".strip()
#     video_file = r"D:\study life\university\competition\competition\2025_CS_application_ability_competition\test.mp4".strip()
#     split_video(srt_file, video_file)
