
import sys
from pathlib import Path
import streamlit.web.cli as stcli
import streamlit.web.bootstrap as bootstrap

def run_streamlit_app(current_dir, port=7000, max_port=8510):
    """
    通过程序方式启动Streamlit应用
    
    Args:
        current_dir: 当前目录路径
        port: 起始端口号
        max_port: 最大尝试端口号
    """
    success = False
    current_port = port
    
    # 获取配置文件路径
    config_path = Path(current_dir) / '.streamlit' / 'config.toml'
    
    # 主脚本路径
    script_path = Path(current_dir) / 'main5.py'
    
    while current_port <= max_port and not success:
        try:
            print(f'\n尝试端口 {current_port}...')
            
            # 修改config.toml中的端口配置
            update_config_port(config_path, current_port)
            
            # 定义命令行参数
            args = [
                "run",
            ]
            
            # 调用内部方法启动应用
            stcli._main_run_clExplicit(
                file=str(script_path),
                args=args,
            )
            
            success = True
            
        except Exception as e:
            print(f'端口 {current_port} 启动失败: {str(e)}')
            current_port += 1
    
    if not success:
        raise RuntimeError(f"端口 {port}-{max_port} 全部尝试失败")

def update_config_port(config_path, port):
    """
    更新config.toml中的端口配置
    
    Args:
        config_path: 配置文件路径
        port: 新的端口号
    """
    if not config_path.exists():
        # 如果配置文件不存在，创建一个新的
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('[global]\ndevelopmentMode = false\n\n[server]\nport = {}\n'.format(port))
        return
    
    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找并更新端口配置
    port_line_found = False
    server_section_found = False
    
    for i, line in enumerate(lines):
        if '[server]' in line:
            server_section_found = True
        elif server_section_found and 'port' in line:
            lines[i] = f'port = {port}\n'
            port_line_found = True
            break
    
    # 如果没有找到端口配置，添加它
    if not port_line_found:
        if server_section_found:
            # 在[server]部分添加端口配置
            for i, line in enumerate(lines):
                if '[server]' in line:
                    lines.insert(i + 1, f'port = {port}\n')
                    break
        else:
            # 添加[server]部分和端口配置
            lines.append('\n[server]\n')
            lines.append(f'port = {port}\n')
    
    # 写回配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

if __name__ == '__main__':
    try:
        # 获取当前目录（兼容exe打包和直接运行）
        if getattr(sys, 'frozen', False):
            # 打包后使用exe所在目录
            current_dir = Path(sys.executable).parent.resolve()
        else:
            # 直接运行时使用脚本所在目录
            current_dir = Path(__file__).parent.resolve()
        
        # 主脚本路径
        main_script = current_dir / 'main5.py'
        
        # 检查主脚本是否存在
        if not main_script.exists():
            raise FileNotFoundError(f'主程序未找到: {main_script}')
            
        # 启动Streamlit应用
        print('正在启动应用...')
        run_streamlit_app(current_dir)
        
    except Exception as e:
        print(f'\n错误发生: {str(e)}')
        # 清理临时文件
        temp_dir = current_dir / 'temp_videos'
        if temp_dir.exists():
            for f in temp_dir.glob('*'):
                try:
                    f.unlink()
                except Exception as cleanup_error:
                    print(f'清理临时文件失败: {cleanup_error}')
        input('按回车键退出...')
        sys.exit(1)