# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
import time
import requests
from pathlib import Path
from src.utils.path_handler import get_info_path, get_relative_path
# from utils.path_handler import get_info_path, get_relative_path
# from faster_whisper import WhisperModel

# 讯飞API配置
lfasr_host = 'http://raasr.xfyun.cn/api'
api_prepare = '/prepare'
api_upload = '/upload'
api_merge = '/merge'
api_get_progress = '/getProgress'
api_get_result = '/getResult'
file_piece_size = 10485760  # 10MB分片

class XunfeiAPIWrapper:
    def __init__(self, appid, secret_key):
        self.appid = appid
        self.secret_key = secret_key
        self.slice_gen = SliceIdGenerator()

    def _generate_signature(self, ts):
        """生成API签名"""
        md5 = hashlib.md5((self.appid + ts).encode()).hexdigest()
        signature = hmac.new(self.secret_key.encode(), md5.encode(), hashlib.sha1).digest()
        return base64.b64encode(signature).decode()

    def _call_api(self, endpoint, params, files=None):
        """统一API调用方法（添加响应日志）"""
        url = lfasr_host + endpoint
        response = requests.post(url, data=params, files=files)
        
        # 新增调试输出
        print("\n[DEBUG] API Response Raw:")
        print("Endpoint:", endpoint)
        print("Status Code:", response.status_code)
        print("Headers:", response.headers)
        try:
            json_data = response.json()
            print("JSON Body:")
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print("Non-JSON Response:", response.text)
        
        # 将原始响应存入文件
        debug_path = get_relative_path('debug', 'api_response.json')
        with open(debug_path, 'a', encoding='utf-8') as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {endpoint} ===\n")
            f.write(json.dumps(json_data, indent=2, ensure_ascii=False))
        
        if response.status_code != 200:
            raise RuntimeError(f"HTTP错误: {response.status_code}")
            
        result = response.json()
        if result.get("ok") != 0:
            raise RuntimeError(f"API业务错误: {result.get('failed')}")
        return result

    def process_audio(self, file_path):
        """完整处理流程"""
        # 1. 预处理
        prepare_params = {
            "app_id": self.appid,
            "signa": self._generate_signature(str(int(time.time()))),
            "ts": str(int(time.time())),
            "file_len": str(os.path.getsize(file_path)),
            "file_name": os.path.basename(file_path),
            "slice_num": str((os.path.getsize(file_path) + file_piece_size - 1) // file_piece_size)
        }
        prepare_res = self._call_api(api_prepare, prepare_params)
        task_id = prepare_res["data"]

        # 2. 分片上传
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(file_piece_size)
                if not chunk:
                    break
                
                upload_params = {
                    "app_id": self.appid,
                    "signa": self._generate_signature(str(int(time.time()))),
                    "ts": str(int(time.time())),
                    "task_id": task_id,
                    "slice_id": self.slice_gen.getNextSliceId()
                }
                self._call_api(api_upload, upload_params, 
                             files={"filename": (None, b''), "content": chunk})

        # 3. 合并文件
        merge_params = {
            "app_id": self.appid,
            "signa": self._generate_signature(str(int(time.time()))),
            "ts": str(int(time.time())),
            "task_id": task_id,
            "file_name": os.path.basename(file_path)
        }
        self._call_api(api_merge, merge_params)

        # 4. 等待处理完成
        while True:
            progress_params = {
                "app_id": self.appid,
                "signa": self._generate_signature(str(int(time.time()))),
                "ts": str(int(time.time())),
                "task_id": task_id
            }
            progress = self._call_api(api_get_progress, progress_params)
            
            if json.loads(progress["data"])["status"] == 9:
                break
            time.sleep(15)

        # 5. 获取结果
        result_params = {
            "app_id": self.appid,
            "signa": self._generate_signature(str(int(time.time()))),
            "ts": str(int(time.time())),
            "task_id": task_id
        }
        # result_params = {
        #     "app_id": self.appid,
        #     "signa": self._generate_signature(str(int(time.time()))),
        #     "ts": str(int(time.time())),
        #     "task_id": "81908301da6c493dbea0f3e53e418989",
        # }
        return self._call_api(api_get_result, result_params)

class SliceIdGenerator:
    """分片ID生成器（保持官方实现）"""
    def __init__(self):
        self.__ch = 'aaaaaaaaa`'

    def getNextSliceId(self):
        ch = self.__ch
        j = len(ch) - 1
        while j >= 0:
            cj = ch[j]
            if cj != 'z':
                ch = ch[:j] + chr(ord(cj) + 1) + ch[j + 1:]
                break
            else:
                ch = ch[:j] + 'a' + ch[j + 1:]
                j = j - 1
        self.__ch = ch
        return self.__ch

def audio_to_words2(audio_path):
    """
    保持原有函数签名
    返回格式示例：[0.00 - 5.00] 你好，世界
    """
    try:
        # 加载配置文件
        config_path = Path(__file__).parent.parent / 'config' / 'config.json'
        with open(config_path) as f:
            config = json.load(f)
        
        # 初始化API客户端
        xunfei = XunfeiAPIWrapper(
            appid=config["xunfei"]["app_id"],
            secret_key=config["xunfei"]["secret_key"]
        )

        # 处理音频文件
        result = xunfei.process_audio(audio_path)

        # 生成输出文件
        output_file = get_relative_path('dat', 'result.txt')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # 解析结果并保持原有格式
        with open(output_file, 'w', encoding='utf-8') as f:
            data_str=result.get("data", [])
            data_list = json.loads(data_str)

            for seg in data_list:
                start = float(seg["bg"]) / 1000  # 转换为秒
                end = float(seg["ed"]) / 1000
                text = seg["onebest"]

                f.write(f"[{start:.2f} - {end:.2f}] {text}\n")

        # with open(output_file, 'w', encoding='utf-8') as f:
        #     for seg in result:
        #         start = float(seg["bg"]) / 100  # 转换为秒
        #         end = float(seg["ed"]) / 100
        #         text = seg["onebest"]
        #         f.write(f"[{start:.2f} - {end:.2f}] {text}\n")

        # 更新info.json
        info_path = get_info_path()
        with open(info_path, 'r+') as f:
            data = json.load(f)
            data['txt_file_location'] = str(output_file)
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

        return output_file

    except Exception as e:
        raise RuntimeError(f"音频转写失败: {str(e)}")
# import json
# from faster_whisper import WhisperModel
# import os
# from src.utils.path_handler import get_info_path, get_relative_path

# def audio_to_words1(audio_path, use_cpu=True):
    
#     """
#     将音频文件转换为文本，并将结果存储在info.json中指定的目录下的txt文件中。

#     :param audio_path: 音频文件的路径
#     :param use_cpu: 是否使用CPU进行转换，默认为True
#     :return: 存储文本的文件路径
#     """
#     # 读取配置文件
#     config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
#     # 确保配置文件存在
#     if not os.path.exists(config_path):
#         os.makedirs(os.path.dirname(config_path), exist_ok=True)
#         default_config = {
#             "app_settings": {"default_output_path": "./output"},
#             "api_settings": {"max_retries": 3},
#             "setting1": {"mode": ["cpu"]}
#         }
#         with open(config_path, 'w') as f:
#             json.dump(default_config, f)
#     else:
#         with open(config_path, 'r') as f:
#             config = json.load(f)

#     # 添加默认setting1配置（兼容现有配置文件）
#     config.setdefault('setting1', {'mode': ['cpu']})

#     # 根据use_cpu参数更新配置
#     if use_cpu:
#         config['setting1']['mode'] = ['cpu']
#     else:
#         config['setting1']['mode'] = ['gpu0']

#     # 保存更新后的配置
#     with open(config_path, 'w') as f:
#         json.dump(config, f, indent=4)

#     # 加载模型
#     # 修改模型加载路径
#     model_path = get_relative_path('model', 'faster-whisper-small')
#     model = WhisperModel(model_path, device="cpu" if use_cpu else "cuda", compute_type="int8" if use_cpu else "float16")

#     # 进行音频转录
#     segments, info = model.transcribe(audio_path)

#     # 读取info.json文件
#     info_path = get_info_path()
#     try:
#         with open(info_path, 'r') as f:
#             info_data = json.load(f)
#     except Exception as e:
#         raise RuntimeError(f"无法读取配置文件: {str(e)}")

#     # 生成输出文件路径
#     output_file = get_relative_path('dat', 'result.txt')
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)

#     try:
#         with open(output_file, 'w', encoding='utf-8') as f:
#             for segment in segments:
#                 f.write(f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}\n")
#     except IOError as e:
#         raise RuntimeError(f"文件写入失败: {str(e)}")

#     # 更新info.json
#     try:
#         with open(info_path, 'r+') as f:
#             data = json.load(f)
#             data['txt_file_location'] = str(output_file)
#             f.seek(0)
#             json.dump(data, f, indent=2, ensure_ascii=False)
#             f.truncate()
#             return data['txt_file_location']
#     except Exception as e:
#         raise RuntimeError(f"配置文件更新失败: {str(e)}")

    
    

def audio_to_words(audio_path,processing_mode="Xunfei_api"):
    
    if processing_mode == "Xunfei_api":
        return audio_to_words2(audio_path)
    # else:  
    #     use_cpu = True if processing_mode == "CPU" else False
    #     return audio_to_words1(audio_path,use_cpu)

# if __name__ == '__main__':
#     # 测试用例（保持原有格式）
#     import argparse
#     parser = argparse.ArgumentParser(description='音频转文字测试')
#     parser.add_argument('--audio_path', type=str, default=r'D:\Projects\v1.1\AI\output_audios\消除国家穷人翻身  一个被政治斗争摧毁的理想！【托洛茨基系列集合】 - 1.消除国家穷人翻身  一个被政治斗争摧毁的理想！【托洛茨基系列集合】(Av113921507791587,P1)_trimmed.mp3')
#     parser.add_argument('--use_cpu', action='store_true')
#     args = parser.parse_args()

#     try:
#         result_path = audio_to_words(args.audio_path, args.use_cpu)
#         print(f"转换成功！结果文件：{result_path}")

#         with open(result_path, 'r', encoding='utf-8') as f:
#             print("\n前5行预览:")
#             for _ in range(5):
#                 line = f.readline()
#                 if not line: break
#                 print(line.strip())

#     except Exception as e:
#         print(f"错误发生: {str(e)}")
#         exit(1)