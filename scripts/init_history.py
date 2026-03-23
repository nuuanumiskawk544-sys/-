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
        
        # 假设 AI 返回 {"history": ["...", "..."]}
        res_json = json.loads(response.choices[0].message.content)
        # 兼容不同返回格式
        new_history = res_json.get("history", list(res_json.values())[0])

        # 读取现有 JSON 状态
        current_data = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)

        # 合并记忆：前 15 章放在最前面
        old_history = current_data.get("plot_history", [])
        # 过滤掉可能重复的（如果之前的 3 条里有前 15 章的内容）
        current_data["plot_history"] = new_history + old_history
        current_data["last_update_chapter"] = max(current_data.get("last_update_chapter", 15), 15)

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 初始化成功！当前记忆总条数：{len(current_data['plot_history'])}")
        for i, h in enumerate(current_data["plot_history"][:15]):
            print(f"  [第{i+1}章提炼]: {h}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")

if __name__ == "__main__":
    init_memories()
