import os
import json
import re
from openai import OpenAI

# ======= 核心配置区 =======
STATE_FILE = "world_state.json"
MODEL_NAME = "deepseek-chat"
# 1. 大纲文件（用于提炼核心设定）
OUTLINE_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt" 
# 2. 故事原文文件（用于提炼开篇和既定事实）
STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了.txt" 
# =========================

def get_summary(client, prompt_text, max_chars=15):
    """通用摘要生成函数"""
    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"你是一个剧情提炼专家。请用{max_chars}字以内总结。"},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.3
        )
        return res.choices[0].message.content.strip().replace('"', '')
    except:
        return None

def heal_history():
    api_key = os.getenv("AI_API_KEY")
    if not api_key: return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    new_plot_history = []

    # --- 第一步：提炼【大纲】核心设定 ---
    if os.path.exists(OUTLINE_FILE):
        print(f"📖 正在提炼大纲设定: {OUTLINE_FILE}...")
        with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
            content = f.read(20000)
        summary = get_summary(client, f"总结此大纲的核心设定与金手指：\n{content}", 20)
        if summary: new_plot_history.append(f"【核心设定】: {summary}")

    # --- 第二步：提炼【故事原文】的关键节点 ---
    if os.path.exists(STORY_FILE):
        print(f"📜 正在提炼故事原文: {STORY_FILE}...")
        with open(STORY_FILE, "r", encoding="utf-8") as f:
            full_text = f.read()
            # 提炼开头（确定身份）
            start_summary = get_summary(client, f"总结原文开篇事件：\n{full_text[:20000]}")
            # 提炼结尾（确定目前进度）
            end_summary = get_summary(client, f"总结原文截止到目前的最新进度：\n{full_text[-20000:]}")
            
            if start_summary: new_plot_history.append(f"【原文起点】: {start_summary}")
            if end_summary: new_plot_history.append(f"【原文终点】: {end_summary}")

    # --- 第三步：提炼【Chapters】文件夹独立章节 ---
    if os.path.exists("chapters"):
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        files.sort(key=lambda x: int(re.match(r'(\d+)', x).group(1)) if re.match(r'(\d+)', x) else 999)

        for file_name in files:
            print(f"🔄 提炼章节: {file_name}")
            with open(os.path.join("chapters", file_name), "r", encoding="utf-8") as f:
                content = f.read(1200)
            summary = get_summary(client, content)
            if summary: new_plot_history.append(summary)

    # --- 第四步：写入 JSON ---
    data = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: data = {}
    
    data["plot_history"] = new_plot_history
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("-" * 30)
    print(f"🚀 全量记忆同步完成！当前记忆链条长度: {len(new_plot_history)}")

if __name__ == "__main__":
    heal_history()
