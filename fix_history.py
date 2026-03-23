import os
import json
import re
from openai import OpenAI

# ======= 核心配置区 =======
STATE_FILE = "world_state.json"
MODEL_NAME = "deepseek-chat"
OUTLINE_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt" 
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
    except Exception as e:
        print(f"❌ 调用AI失败: {e}")
        return None

def heal_history():
    api_key = os.getenv("AI_API_KEY")
    if not api_key: return
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 1. 加载现有数据
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = {}
    else:
        data = {}

    # 初始化记忆列表
    if "plot_history" not in data:
        data["plot_history"] = []
    
    current_history = data["plot_history"]

    # 2. 【永久储存逻辑】如果记忆为空，则提炼原文和大纲（仅此一次）
    if not current_history:
        print("🆕 检测到记忆空白，开始初始化原文和大纲提炼...")
        
        # 提炼大纲
        if os.path.exists(OUTLINE_FILE):
            with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
                content = f.read(20000)
            summary = get_summary(client, f"总结此大纲的核心设定与金手指：\n{content}", 20)
            if summary: current_history.append(f"【核心设定】: {summary}")

        # 提炼原文开头和结尾
        if os.path.exists(STORY_FILE):
            with open(STORY_FILE, "r", encoding="utf-8") as f:
                full_text = f.read()
                start_s = get_summary(client, f"总结原文开篇：\n{full_text[:50000]}")
                end_s = get_summary(client, f"总结原文最新进度：\n{full_text[-50000:]}")
                if start_s: current_history.append(f"【原文起点】: {start_s}")
                if end_s: current_history.append(f"【原文终点】: {end_s}")
        print("✅ 初始背景提炼完成。")
    else:
        print(f"ℹ️ 已有历史记忆 {len(current_history)} 条，跳过原文和大纲提炼。")

    # 3. 【增量更新逻辑】只提炼 chapters 中未记录的章节
    if os.path.exists("chapters"):
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        # 按数字编号排序（001, 002...）
        files.sort(key=lambda x: int(re.match(r'(\d+)', x).group(1)) if re.match(r'(\d+)', x) else 999)

        # 获取当前最大的章节编号（通过 last_update_chapter 识别）
        last_chapter_num = data.get("last_update_chapter", 0)
        
        for file_name in files:
            chapter_num = int(re.match(r'(\d+)', file_name).group(1))
            
            # 只有当文件名编号大于记录的最后章节编号时，才进行提炼
            if chapter_num > last_chapter_num:
                print(f"🔄 发现新章节，正在提炼增量记忆: {file_name}...")
                with open(os.path.join("chapters", file_name), "r", encoding="utf-8") as f:
                    content = f.read(1200)
                summary = get_summary(client, content)
                if summary:
                    current_history.append(summary)
                    # 同步更新 last_update_chapter
                    data["last_update_chapter"] = chapter_num
            else:
                # 已经提炼过的章节直接跳过
                continue

    # 4. 写回 JSON
    data["plot_history"] = current_history
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("-" * 30)
    print(f"🚀 增量同步完成！当前总计记忆条数: {len(current_history)}")

if __name__ == "__main__":
    heal_history()
