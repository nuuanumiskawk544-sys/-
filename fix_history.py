import os
import json
import re
from openai import OpenAI

# ======= 配置区 =======
STATE_FILE = "world_state.json"
MODEL_NAME = "deepseek-chat"
# 你的原文/初始大纲文件名
ORIGINAL_STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt" 
# =====================

def heal_history():
    api_key = os.getenv("AI_API_KEY")
    if not api_key: return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    new_plot_history = []

    # 1. 【新增】提炼原文/初始背景记忆
    if os.path.exists(ORIGINAL_STORY_FILE):
        print(f"📖 正在提炼原文背景记忆...")
        with open(ORIGINAL_STORY_FILE, "r", encoding="utf-8") as f:
            origin_content = f.read(3000) # 只取前3000字提炼核心背景
        
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": f"请用20字以内总结这段网文的初始背景和金手指设定：\n{origin_content}"}]
            )
            new_plot_history.append(f"背景：{res.choices[0].message.content.strip()}")
        except: pass

    # 2. 提炼章节记忆
    if os.path.exists("chapters"):
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        files.sort(key=lambda x: int(re.match(r'(\d+)', x).group(1)) if re.match(r'(\d+)', x) else 999)

        for file_name in files:
            print(f"🔄 提炼章节: {file_name}")
            with open(os.path.join("chapters", file_name), "r", encoding="utf-8") as f:
                content = f.read(1500)
            try:
                res = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": "15字以内总结章节核心事件。"},
                              {"role": "user", "content": content}]
                )
                new_plot_history.append(res.choices[0].message.content.strip())
            except: continue

    # 3. 写入 JSON
    data = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    data["plot_history"] = new_plot_history
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ 全量记忆（含原文背景）已同步！")

if __name__ == "__main__":
    heal_history()
