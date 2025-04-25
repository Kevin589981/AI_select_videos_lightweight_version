import os
#from moviepy.editor import VideoFileClip #新版本moviepy移除了editor
from moviepy.video.io.VideoFileClip import VideoFileClip
from src.utils.path_handler import get_relative_path, ensure_dir_exists, get_info_path
import json

def extract_audio_from_video(video_path):
    """
    从视频文件中提取音频
    :param video_path: 视频文件路径
    :return: 音频对象 (AudioFileClip)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件 {video_path} 不存在")
    
    video_clip = VideoFileClip(video_path)
    audio_clip = video_clip.audio
    
    if audio_clip is None:
        video_clip.close()  # 关闭视频文件释放资源
        raise ValueError(f"视频文件 {video_path} 没有音频轨道")
    
    return video_clip, audio_clip  # 返回 video_clip 和 audio_clip

def save_audio( video_path, output_dir):
    video_clip, audio_clip=extract_audio_from_video(video_path)
    
    # 使用统一路径处理
    output_dir = ensure_dir_exists(get_relative_path(output_dir))
    
    # 生成输出文件名
    video_filename = os.path.basename(video_path)
    base_name = os.path.splitext(video_filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}.mp3")

    try:
        # 更新info.json
        info_data = {
            "src_file_location": str(get_relative_path(video_path)),
            "audio_file_location": str(output_path)
        }
        
        # 写入info.json
        with open(get_info_path(), 'w') as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        raise RuntimeError(f"配置文件操作失败: {str(e)}")

    try:
        # 验证音频剪辑有效性
        if not hasattr(audio_clip, 'write_audiofile'):
            raise ValueError("无效的音频剪辑对象")
        
        # 保存音频文件
        audio_clip.write_audiofile(output_path, bitrate='192k', codec='libmp3lame')
        return output_path
    except Exception as e:
        raise RuntimeError(f"音频文件保存失败: {str(e)}")
    finally:
        # 确保资源被释放
        audio_clip.close()
        video_clip.close()

# def main(video_path, output_dir):
#     """
#     主流程：提取音频并保存
#     """
#     video_clip, audio_clip = extract_audio_from_video(video_path)
#     saved_path = save_audio(video_clip, audio_clip, video_path, output_dir)
#     print(f"[成功] 音频已保存至：{saved_path}")

# if __name__ == "__main__":
#     video_path = r"D:\Projects\test\截取片段\片段1_[11.00-25.00].mp4"  # 你的视频文件路径
#     output_dir = r"D:\Projects\AI\output_audios"  # 输出目录
    
#     main(video_path, output_dir)