import os
import json
from openai import OpenAI

# ======= 配置区 =======
STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了.txt"
STATE_FILE = "world_state.json"
MODEL_NAME = "deepseek-chat"
# =====================

def init_memories():
    api_key = os.getenv("AI_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    if not os.path.exists(STORY_FILE):
        print(f"❌ 错误：找不到原文文件 {STORY_FILE}")
        return

    print("📖 正在读取前 15 章原文进行深度提炼...")
    with open(STORY_FILE, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 简单粗暴切分法：取前 30000 字（大致覆盖前15章）
    sample_text = full_text[:30000]

    prompt = f"""
    你是一个网文编辑，请阅读下面《四合院》同人小说的前 15 章片段，
    将其提炼为 15 条极简的剧情摘要（每条 15 字以内）。
    
    格式要求：直接返回一个 JSON 数组，例如 ["内容1", "内容2"...]
    
    【原文片段】：
    {sample_text}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        # 解析 AI 返回的原始数据
        res_json = json.loads(response.choices[0].message.content)
        
        # 🚨 【修复核心】判断返回类型
        if isinstance(res_json, list):
            # 如果 AI 直接返回了 ["第1章...", "第2章..."]
            new_history = res_json
        elif isinstance(res_json, dict):
            # 如果 AI 返回了 {"history": [...]} 或 {"data": [...]}
            # 获取字典中第一个值（通常就是我们要的列表）
            new_history = list(res_json.values())[0] 
        else:
            new_history = []

        # 读取现有 JSON 状态（如果存在）
        current_data = {
            "last_update_chapter": 15,
            "plot_history": [],
            "key_npcs": {},
            "current_inventory": "随身空间（产肉/蔬菜/灵泉）"
        }
        
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                try:
                    current_data = json.load(f)
                except: pass

        # 确保 new_history 是列表并合并
        if isinstance(new_history, list):
            # 将新提炼的 15 条作为基础，再加上可能已经存在的后续记忆
            # 如果你只想保留这 15 条，可以直接 current_data["plot_history"] = new_history
            current_data["plot_history"] = new_history + current_data.get("plot_history", [])
            # 简单去重（防止重复运行导致记忆翻倍）
            current_data["plot_history"] = list(dict.fromkeys(current_data["plot_history"]))
        
        current_data["last_update_chapter"] = max(current_data.get("last_update_chapter", 15), 15)

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 初始化成功！当前记忆总条数：{len(current_data['plot_history'])}")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
if __name__ == "__main__":
    init_memories()
