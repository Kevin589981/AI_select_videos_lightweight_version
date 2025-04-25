import os
from pathlib import Path
import sys
def get_project_root():
    """智能获取项目根目录"""
    if getattr(sys, 'frozen', False):
        # 打包环境：指向exe所在目录的上级
        exe_dir = Path(sys.executable).parent
        # 开发环境保持原逻辑
        if (exe_dir / 'src').exists():  # 调试模式
            return exe_dir
        return exe_dir.parent  # 正式发布模式
    return Path(__file__).parent.parent.parent

def get_data_path(*subpaths):
    """获取外部数据路径"""
    root = get_project_root()
    # 优先尝试同级目录的_data文件夹
    external_path = root / '_data' / Path(*subpaths)
    if external_path.exists():
        return external_path
    # 回退到原始项目结构
    return root / Path(*subpaths)

def get_relative_path(*path_parts):
    """构建基于项目根目录的相对路径"""
    return os.path.join(get_project_root(), *path_parts)

def ensure_dir_exists(path):
    """确保目录存在，不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path

# 预定义常用路径
def get_info_path():
    return get_relative_path('dat', 'info.json')
    
def get_chosen_result_path():
    return get_relative_path('dat', 'chosen_result.txt')

def get_model_dir():
    return get_relative_path('model')

def get_output_dir(name='outputs'):
    return ensure_dir_exists(get_relative_path(name))