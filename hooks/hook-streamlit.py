# from PyInstaller.utils.hooks import copy_metadata
# datas = copy_metadata('streamlit')
from PyInstaller.utils.hooks import collect_all
datas, binaries, hiddenimports = collect_all('streamlit', include_py_files=False, include_datas=['**/*.*'])