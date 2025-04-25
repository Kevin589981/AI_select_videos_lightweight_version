import json
import requests
import os
from src.utils.path_handler import get_chosen_result_path
# from utils.path_handler import get_chosen_result_path
def query(robot_string,user_string,model="Qwen/Qwen2.5-72B-Instruct"):#"deepseek-ai/DeepSeek-R1",):
    url = "https://api.siliconflow.cn/v1/chat/completions"
    max_retries = 3
    timeout = 20  # 20秒超时
    retry_count = 0

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": robot_string
            },
            {
                "role": "user",
                "content": user_string
            }
        ],
        "stream": True,
        "max_tokens": 1000,
        "stop": None,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "n": 1,
        "response_format": {"type": "text"},
        
    }

    headers = {
        "Authorization": "Bearer sk-tnzjzxdzohgtpsuxhjwrynkjckgbyihrlbioortpppiaftuo",
        "Content-Type": "application/json"
    }

    while retry_count < max_retries:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()  # 检查 HTTP 错误（如 4xx/5xx）
            
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                retry_count += 1
                print(f"请求失败，状态码: {response.status_code}，正在重试 ({retry_count}/{max_retries})")
                continue

            print("请求成功，正在处理")
            full_content = ''

            # 流式数据处理保持不变
            for chunk in response.iter_lines():
                if not chunk or chunk.startswith(b":"):
                    continue

                chunk_str = chunk.decode('utf-8').strip()
                if not chunk_str.startswith("data: "):
                    continue

                json_str = chunk_str[6:].strip()
                if json_str == "[DONE]":
                    print("\nStream completed with [DONE]")
                    break

                try:
                    json_data = json.loads(json_str)
                    if "choices" in json_data and len(json_data["choices"])>0:
                        content = json_data["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end='', flush=True)
                            full_content += content
                except Exception as e:
                    print(f"\n数据处理异常: {e}")

            # 保存结果
            output_path = str(get_chosen_result_path())
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(full_content)
                print(f"\n结果已保存至 {output_path}")
            
            return True
        
        except requests.exceptions.Timeout:
            retry_count += 1
            print(f"请求超时，正在重试 ({retry_count}/{max_retries})")
            if retry_count >= max_retries:
                print("超过最大重试次数")
                return False

        except requests.exceptions.HTTPError as e:
            print(f"\nHTTP 请求失败，状态码: {e.response.status_code}")
            print(f"错误详情: {e.response.text}")
            return False

        except Exception as e:
            print(f"\n未知错误: {e}")
            return False

    return False

# def query(robot_string, user_string, model="deepseek-ai/DeepSeek-V3",):
#     print("暂时略过这一步请求API以便调试")
#     print(f"{os.getcwd()}\\dat\\chosen_result.txt")
#     return True

# if __name__ == '__main__':
#     import argparse
    
#     parser = argparse.ArgumentParser(description='API测试')
#     parser.add_argument('--robot', type=str, default="你是一个字幕筛选机器人,下面我会发送一些带有时间戳的字幕给你，请你根据语义，筛选出若干最有意思的视频片段的字幕,（可能包括了连续的几段字幕，如果两段字幕的时间戳间隔过长，则认为是两个视频片段，否则就视为1个视频片段，判断标准是两个时间戳间隔相差大于1秒），回答我时格式只要和我发送给你的字幕时间戳的格式一致（即从某一时刻到某一时刻），回答中每行是每一整段的时间戳，不要回答任何与时间戳无关的内容:",
#     #parser.add_argument('--robot', type=str, default="",
#                       help='系统提示词（默认使用预置提示）')
#     parser.add_argument('--user', type=str, default="[0.00 - 2.00] 1902年的一个夜晚\n[2.00 - 4.00] 西伯利亚背加尔湖边\n[4.00 - 5.00] 耶尔库斯克\n[5.00 - 7.00] 一名叫布朗士坦的流放犯\n[7.00 - 9.00] 从拉干草的马车上偷偷跳了出来\n[9.00 - 11.00] 跑到约定好的会合地点\n[11.00 - 13.00] 约定的人拿出一张假的通行证\n[13.00 - 16.00] 让他提供一个可以写在通行证上的安全的姓名\n[16.00 - 18.00] 布朗士坦想起了他在奥德萨监狱市\n[18.00 - 20.00] 押送他的一个御族\n[20.00 - 22.00] 于是他在自己的通行证上\n[22.00 - 24.00] 匆匆写下了御族的名字\n[24.00 - 25.00] 脱落刺激\n[25.00 - 27.00] 然后带着这个名字\n[27.00 - 29.00] 他上了创业整个西伯利亚的货车\n[29.00 - 31.00] 他不曾想\n[31.00 - 33.00] 这个他随便起来逃难的名字\n[33.00 - 36.00] 在后来发动了数次全国范围内的革命\n[36.00 - 37.00] 用这个名字集合力量\n[37.00 - 39.00] 全权指挥了十月革命\n[39.00 - 40.00] 也是用这个名字\n[40.00 - 42.00] 在短短一年多的时间里\n[42.00 - 43.00] 把共产党的部队\n[43.00 - 44.00] 从十月革命时的几千人\n[44.00 - 46.00] 变成了五百万人\n[46.00 - 48.00] 这同样也是世界上第一只红军\n[48.00 - 49.00] 还有\n[49.00 - 51.00] 后来斯大林为了抹杀这个名字的一切\n[51.00 - 54.00] 出决了六十八万共产党员和红军将领\n[54.00 - 56.00] 也让脱落刺激这个名字\n[56.00 - 57.00] 成为反革命的代名词\n[57.00 - 58.00] 但即使这样\n[58.00 - 60.00] 脱落刺激依然没有被战胜\n[60.00 - 61.00] 八十年代\n[61.00 - 62.00] 他被苏共平反\n[62.00 - 63.00] 全世界的革命著作\n[63.00 - 66.00] 也开始基于他应有的革命攻击\n[66.00 - 68.00] 他的共产主义世界的美丽上向\n[68.00 - 69.00] 以及连色全世界工人阶级\n[69.00 - 71.00] 进行无限革命的斗争思想\n[71.00 - 73.00] 开始重新影响全人类\n[73.00 - 74.00] 接下来\n[74.00 - 75.00] 我们就通过脱落刺激\n[75.00 - 77.00] 这个被埋葬于历史当中的人物的经历\n[77.00 - 79.00] 看看他的理想与智慧\n[79.00 - 81.00] 也看看他的恐怖与狂妄\n[81.00 - 83.00] 竟然去理解那个我们最熟悉\n[83.00 - 84.00] 但却已经不认识的词语\n[84.00 - 85.00] 共产主义\n[89.00 - 92.00] 脱落刺激出生在一个富裕的\n[92.00 - 93.00] 犹太农庄家庭\n[93.00 - 96.00] 父亲从俄国的农奴制改革中祸意\n[96.00 - 98.00] 离开城市黑暗的犹太社区\n[98.00 - 99.00] 来到新开墾的土地上\n[99.00 - 100.00] 靠自己的精明与勤劳\n[100.00 - 102.00] 在如今乌克兰的赫尔松大平院上\n[102.00 - 104.00] 获得了上千畝的土地\n[104.00 - 105.00] 脱落刺激出生时\n[105.00 - 106.00] 他们家已经有了\n[106.00 - 107.00] 几十故宫和用人\n[107.00 - 108.00] 还经营着默访\n[108.00 - 110.00] 与斯大林那种充满家暴\n[110.00 - 112.00] 黑暗悲惨的童年不同\n[112.00 - 114.00] 脱落刺激的童年非常美好\n[114.00 - 116.00] 作为家里的第五个孩子\n[116.00 - 117.00] 不仅物质复族\n[117.00 - 118.00] 父母和姐姐们\n[118.00 - 119.00] 也给予了足够的关爱",
#     #parser.add_argument('--user', type=str, default="回答“明白”两个字",
#                       help='用户输入内容（默认使用测试内容）')

#     args = parser.parse_args()

#     try:
#         print("正在发起API请求...")
#         if query(args.robot, args.user):
#             print("\n请求成功！结果已保存至../dat/chosen_result.txt")
            
#             # 读取并展示结果文件内容
#             try:
#                 with open(r"../dat/chosen_result.txt", 'r', encoding='utf-8') as f:
#                     print("\n结果文件内容:")
#                     print(f.read())
#             except Exception as e:
#                 print(f"\n结果文件读取失败: {str(e)}")
#         else:
#             print("\n请求失败，请检查网络连接或API密钥")
#     except Exception as e:
#         print(f"\n发生未预期的错误: {str(e)}")
