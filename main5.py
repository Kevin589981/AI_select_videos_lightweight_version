import sys
from io import StringIO
import streamlit as st
import os
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from src.video_to_audio import save_audio # ,extract_audio_from_video
from src.audio_to_words import audio_to_words
from src.video_to_parts import split_video
from src.query import query
from src.utils.path_handler import get_project_root, get_relative_path, get_info_path, get_chosen_result_path
import threading
# import platform
# import subprocess
# from streamlit_extras.stylable_container import stylable_container
from streamlit.components.v1 import html
import base64
import queue

# 设置页面标题和布局
st.set_page_config(
    page_title="基于AI的视频高光时刻生成 light版",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 在文件顶部初始化 session_state
if 'video_segments_cache' not in st.session_state:
    st.session_state.video_segments_cache = {}


# 全局样式
st.markdown("""
<style>        
    /* 专门针对开始处理按钮的样式 */
    div.stButton > button:first-child[data-testid="baseButton-secondary"] {
        background-color: #4e73df !important;
        color: white !important;
        border: none !important;
    }
    div.stButton > button:first-child[data-testid="baseButton-secondary"]:hover {
        background-color: #3a56b0 !important;
    }

    /* 主页面背景 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* 卡片悬停效果 */
    .hover-card {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .hover-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* 统一字体 */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 进度条美化 */
    /* 最精确的选择器 */
    div[data-testid="stProgress"] > div > div > div {
        background-color: white !important;
        border-radius: 10px;
        height: 10px;
    }
    
    div[data-testid="stProgress"] > div > div > div > div {
        background-color: #4e73df !important;
        background-image: linear-gradient(
            to right, 
            #4e73df, #3a56b0
        ) !important;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# 添加项目根目录到环境变量
project_root = str(get_project_root())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化session state
if 'real_video_path' not in st.session_state:
    st.session_state.real_video_path = None


# 页面标题
st.markdown("""
<h1 style='text-align: center; 
            color: #2c3e50; 
            font-size: 2.5em; 
            margin-bottom: 20px;
            padding: 10px;
            background: linear-gradient(to right, #e6f0ff, #f8f9fa);
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1)'>
    🎬 基于AI的视频高光时刻生成
</h1>
""", unsafe_allow_html=True)

def select_video_file():# result_queue):
    st.session_state.select_file_button_disabled = True
    try:
        # 添加Tkinter事件循环保护
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', 1)
        root.update_idletasks()  # 强制更新窗口状态
        selected_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov"), ("所有文件", "*.*")]
        )
        root.update()  # 确保窗口完全关闭
        root.quit()  # 彻底退出主循环
        print(selected_path)
        if selected_path:
            
            st.session_state.real_video_path = Path(selected_path)
            # result_queue.put(Path(selected_path))
    except Exception as e:
        st.error(f"文件选择失败: {str(e)}")
    finally:
        st.session_state.select_file_button_disabled = False


# 在侧边栏代码区域修改输出容器
with st.sidebar:
    # 添加侧边栏样式（仅改变背景色）
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #e6f0ff !important;
            border-right: 1px solid #cce0ff;
        }
        
        /* 侧边栏标题样式 */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p {
            color: #2c3e50 !important;
        }
        
        /* 单选按钮选中状态 */
        [data-testid="stSidebar"] .st-ck {
            background: #4e73df;
        }
        
        /* 输入框边框 */
        [data-testid="stSidebar"] .stTextInput input {
            border: 1px solid #aac6ff !important;
        }
        
        /* 按钮样式 */
        [data-testid="stSidebar"] .stButton>button {
            background-color: #ffffff;
            color: white;
            border: none;
        }
        
        [data-testid="stSidebar"] .stButton>button:hover {
            background-color: #eeeeee;
        }
    </style>
    """, unsafe_allow_html=True)

    # 保持原有的侧边栏内容不变，但为text_input添加key参数
    st.header("设置")
    
    # 新增模型选择
    selected_model = st.selectbox(
        "选择AI模型:（实测Qwen/Qwen2.5-72B-Instruct效率最高）",
        ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-R1", "deepseek-ai/DeepSeek-V3"],
        index=0
    )
    
    processing_mode = st.radio(
        "运算模式:（讯飞API速度最快，轻量版无CPU/GPU处理功能）",
        ["Xunfei_api"],
        index=0,
        key="processing_mode_radio"  # 添加唯一key
    )
    topic = st.text_input(
        "主题 (可选):", 
        "",
        key="topic_text_input"  # 添加唯一key
    )
    path=queue.Queue()
    if hasattr(st.session_state, 'tk_root'):    
                st.session_state.tk_root.quit()
                st.session_state.tk_root.destroy()
                del st.session_state.tk_root
    if st.button("选择视频文件（请勿快速双击）", key="select_file_button"):  # 添加唯一key
        st.session_state.select_file_button_disabled = True
        if hasattr(st.session_state, 'tk_root') and threading.current_thread == threading.current_thread():
            try:
                st.session_state.tk_root.quit()  # 退出主循环
                st.session_state.tk_root.destroy()  # 销毁窗口
                del st.session_state.tk_root  # 从 session_state 移除
            except:
                pass  # 如果窗口已关闭，忽略错误
        try:
            
            # 添加Tkinter事件循环保护
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', 1)
            st.session_state.tk_root=root
            root.update_idletasks()  # 强制更新窗口状态
            selected_path = filedialog.askopenfilename(
                title="选择视频文件",
                filetypes=[("视频文件", "*.mp4 *.avi *.mov"), ("所有文件", "*.*")]
            )
            root.update()  # 确保窗口完全关闭
            root.quit()  # 彻底退出主循环
            
            if selected_path:
                # path.put(Path(selected_path))
                st.session_state.real_video_path = Path(selected_path)
            if hasattr(st.session_state, 'tk_root'):    
                st.session_state.tk_root.quit()
                st.session_state.tk_root.destroy()
                del st.session_state.tk_root

        except Exception as e:
            # st.error(f"文件选择失败: {str(e)}")
            pass
        finally:
            try:
                st.session_state.select_file_button_disabled = False
                # if hasattr(st.session_state, 'tk_root'):    
                #     st.session_state.tk_root.quit()
                #     st.session_state.tk_root.destroy()
                #     del st.session_state.tk_root
            except:
                pass

    if hasattr(st.session_state, 'tk_root'):    
                st.session_state.tk_root.quit()
                st.session_state.tk_root.destroy()
                del st.session_state.tk_root
    # st.session_state.real_video_path=path.get()  
    # result_queue = queue.Queue()
    # st.session_state.select_file_button_disabled = False
    # st.button("选择视频文件", key="select_file_button",disabled=st.session_state.select_file_button_disabled,on_click=select_video_file)# ,args=(result_queue,))  # 添加唯一key
        
    #     # thread=threading.Thread(target=select_video_file,args=(result_queue,))
    #     # thread.start()
    #     # thread.join()
    # #st.session_state.real_video_path=result_queue.get()

    # 替换原有的输出容器
    st.markdown("**实时日志**")
    output_expander = st.expander("查看详情", expanded=True)
    with output_expander:
        scroll_container = st.container()
        output_area = scroll_container.empty()
    
    # 修改后的输出重定向类
    class OutputRedirector(StringIO):
        def __init__(self, container):
            super().__init__()
            self.container = container
            self._stdout = sys.stdout
            self.buffer = []
            
        def write(self, text: str):
            super().write(text)
            self.buffer.append(text)
            # 使用HTML实现滚动效果
            formatted = "<div style='max-height:200px; overflow-y:auto; background:#f8f9fa; padding:10px; border-radius:8px; margin:10px 0;'>"
            formatted += "<div style='font-family: monospace; font-size:0.9em;'>"
            formatted += "<pre style='white-space: pre-wrap; margin:0;'>"
            formatted += "".join(self.buffer[-20:])  # 保留最近20条信息
            formatted += "</pre></div></div>"
            self.container.markdown(formatted, unsafe_allow_html=True)
            self._stdout.write(text)  # 保持原终端输出

    # 创建重定向实例
    _output_redirector = OutputRedirector(output_area)
    sys.stdout = _output_redirector

# 主内容区（保持原有逻辑结构）
if st.session_state.real_video_path and st.session_state.real_video_path.exists():

    
    # 显示视频预览 - 美化版
    with st.container():
        st.markdown("""
        <div style='background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                margin-bottom: 25px;
                text-align: center;'>
            <h3 style='color: #2c3e50;
                    border-bottom: 2px solid #e6f0ff;
                    padding-bottom: 10px;
                    margin-top: 0;'>
                📺 视频预览
            </h3>
        """, unsafe_allow_html=True)
        
        # 视频和元信息并排布局
        col_video, col_info = st.columns([3, 1])
        
        with col_video:
            try:
                with open(st.session_state.real_video_path, 'rb') as f:
                    video_bytes = f.read()
                
                # 带边框的视频播放器
                st.markdown("""
                <div style='border: 1px solid #e6f0ff;
                        border-radius: 8px;
                        overflow: hidden;
                        margin-bottom: 15px;'>
                """, unsafe_allow_html=True)
                
                st.video(video_bytes)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ 视频加载失败: {str(e)}")
        
        with col_info:
            st.markdown("""
            <div style='background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    height: 100%;
                    border: 1px solid #e6f0ff;'>
                <p style='font-weight: bold; 
                        color: #2c3e50;
                        margin-bottom: 15px;
                        font-size: 16px;'>
                    📋 视频信息
                </p>
            """, unsafe_allow_html=True)
            
            # 文件信息展示
            file_info = {
                "名称": st.session_state.real_video_path.name,
                "大小": f"{os.path.getsize(st.session_state.real_video_path)/1024/1024:.2f} MB"
            }
            
            for key, value in file_info.items():
                st.markdown(f"""
                <div style='margin-bottom: 12px;'>
                    <span style='color: #7f8c8d; font-size: 14px;'>{key}</span><br>
                    <span style='color: #2c3e50; font-weight: 500;'>{value}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 保持原有的临时文件处理逻辑（不变）
        temp_dir = Path(get_project_root()) / "temp_videos"
        temp_dir.mkdir(exist_ok=True)
        video_path = temp_dir / st.session_state.real_video_path.name
        with open(video_path, 'wb') as f:
            f.write(video_bytes)


        # st.button() 代码
        if st.button(
            "开始生成高光时刻", 
            type="secondary",  # 使用secondary类型避免冲突
            key="process_button",
            help="点击开始分析视频并生成高光片段",
            use_container_width=True
        ):
            
            progress_bar = st.progress(0)
            status_text = st.empty()


            try:
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
                
                # 1. 视频转音频（保持注释不变）
                status_text.text("正在转换视频到音频...")
                output_dir = get_relative_path('output_audios')
                audio_path = save_audio(video_path, output_dir)
                progress_bar.progress(20)
                
                # 2. 语音转文字（保持注释不变）
                status_text.text("正在生成字幕文件...")
                # use_cpu = (processing_mode == "CPU")
                try:
                    txt_path = audio_to_words(audio_path, processing_mode)
                except Exception as e: 
            
                    status_text.text(f"{processing_mode}请求失败，GPU重新分析...")
                    try:
                        txt_path = audio_to_words(audio_path, processing_mode="GPU")
                    except Exception as e:
                        status_text.text("GPU请求失败，改为尝试CPU分析...")
                        txt_path = audio_to_words(audio_path, processing_mode="CPU")
                
                progress_bar.progress(40)
                
                # 3. 调用API分析（保持注释不变）
                status_text.text("正在请求API分析...")
                
                # 读取提示词模板
                try:
                    with open(get_relative_path('assets/query.json'), 'r', encoding='utf-8') as f:
                        query_template = json.load(f)['query']
                    system_prompt = f"{query_template['first_part']}"
                    if topic != "":
                        system_prompt += f"{query_template['topic']}{topic}"
                    system_prompt += f"{query_template['second_part']}{query_template['whether_to_separate']}"
                except Exception as e:
                    st.error(f"无法加载提示词模板: {str(e)}")
                    progress_bar.progress(0)
                    
                
                # 读取生成的字幕文件内容
                try:
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        subtitles = f.read()
                except Exception as e:
                    st.error(f"无法读取字幕文件: {str(e)}")
                    progress_bar.progress(0)


                    
                # 修改query调用，添加model参数
                if query(system_prompt, subtitles, model=selected_model):
                    status_text.text("API请求成功")
                    progress_bar.progress(60)
                    
                    # 4. 视频分割
                    status_text.text("正在分割视频片段...")
                    video_segments = split_video(
                        get_chosen_result_path(), 
                        str(st.session_state.real_video_path),
                        progress_bar=progress_bar,
                        status_text=status_text
                    )

                    
                    # 更新info.json
                    with open(get_info_path(), 'r+') as f:
                        info_data = json.load(f)
                        info_data['video_segments'] = video_segments
                        f.seek(0)
                        json.dump(info_data, f, indent=2, ensure_ascii=False)
                    
                    progress_bar.progress(100)
                    
                    # # 显示结果
                    # # st.balloons()
                    # with stylable_container(
                    #     key="success_notif",
                    #     css_styles="""
                    #     {
                    #         animation: fadeIn 1.5s;
                    #         background: linear-gradient(135deg, #e6f7ff, #f0f9ff);
                    #         border-left: 4px solid #1890ff;
                    #         padding: 1rem;
                    #         border-radius: 8px;
                    #     }
                    #     @keyframes fadeIn {
                    #         from { opacity: 0; transform: translateY(20px); }
                    #         to { opacity: 1; transform: translateY(0); }
                    #     }
                    #     """
                    # ):
                    #     st.success("处理完成！")
                    
                    st.markdown("""
                    <div style="
                        animation: fadeIn 1.5s;
                        background: linear-gradient(135deg, #e6f7ff, #f0f9ff);
                        border-left: 4px solid #1890ff;
                        padding: 1rem;
                        border-radius: 8px;
                        margin: 1rem 0;
                    ">
                        <div style="display: flex; align-items: center;">
                            <span style="color: #1890ff; font-size: 1.2rem; margin-right: 0.5rem;">✓</span>
                            <span style="color: #262730; font-weight: 500;">处理完成！</span>
                        </div>
                    </div>
                    <style>
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(20px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    </style>
                    """, unsafe_allow_html=True)




                    # 在展示高光时刻的部分修改
                    with st.container():
                        st.markdown("""
                        <div style='background: white;
                                padding: 20px;
                                border-radius: 10px;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                margin-top: 20px;'>
                            <h3 style='color: #2c3e50; 
                                    border-bottom: 2px solid #e6f0ff;
                                    padding-bottom: 8px;'>
                                🌟 生成的高光时刻
                            </h3>
                        """, unsafe_allow_html=True)
                        
                        cols = st.columns(2)
                        
                        for i, segment in enumerate(video_segments):
                            segment_path = Path(segment).absolute()
                            
                            with cols[i % 2]:
                                with st.container():
                                    st.markdown(f"""
                                    <div style='background: #f8f9fa;
                                            padding: 15px;
                                            border-radius: 8px;
                                            margin-bottom: 15px;
                                            border: 1px solid #e6f0ff;'
                                            class='hover-card'>
                                        <p style='font-weight: bold; 
                                                color: #2c3e50;
                                                margin-bottom: 10px;'>
                                            🎥 片段 {i+1}: <code>{segment_path.name}</code>
                                        </p>
                                    """, unsafe_allow_html=True)
                                    
                                    try:
                                        with open(segment_path, "rb") as video_file:
                                            video_bytes = video_file.read()
                                        st.video(video_bytes)
                                        
                                        # 将视频数据转换为 base64
                                        b64_video = base64.b64encode(video_bytes).decode()
                                        
                                        # 使用 JavaScript 创建下载链接
                                        download_script = f"""
                                        <a id="download_{i}" href="data:video/mp4;base64,{b64_video}" 
                                        download="{segment_path.name}" style="display: none;"></a>
                                        <button onclick="document.getElementById('download_{i}').click()" 
                                                style="width: 100%; padding: 8px; background-color: #4e73df; 
                                                    color: white; border: none; border-radius: 5px; 
                                                    cursor: pointer;">
                                            ⬇️ 下载片段
                                        </button>
                                        """
                                        html(download_script, height=50)
                                        
                                    except Exception as e:
                                        st.error(f"无法加载视频: {str(e)}")
                                    
                                    st.markdown("</div>", unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)


                else:
                    st.error("API请求失败，请检查网络连接和API密钥")
                    progress_bar.progress(0)
            
            except Exception as e:
                st.error(f"处理出错: {str(e)}")
                progress_bar.progress(0)
                
    # except Exception as e:
    #     st.error(f"文件读取失败: {str(e)}")

# 新增临时文件清理逻辑
temp_dir = Path(get_project_root()) / "temp_videos"
if temp_dir.exists():
    for f in temp_dir.glob("*"):
        try:
            f.unlink()
        except Exception as e:
            print(f"清理失败 {f.name}: {str(e)}")

if project_root in sys.path:
    sys.path.remove(project_root)


# 在文件底部添加页脚
st.markdown("""
<hr style='margin: 20px 0; border-color: #e6f0ff;'>
<div style='text-align: center; color: #7f8c8d; font-size: 0.9em;'>
    <p>🎥 AI视频高光生成系统</p>
</div>
""", unsafe_allow_html=True)