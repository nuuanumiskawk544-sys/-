import os, json, re
from openai import OpenAI

# 配置与主脚本一致
STATE_FILE = "world_state.json"
MODEL_NAME = "deepseek-chat"

def heal_history():
    api_key = os.getenv("AI_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 1. 获取所有已写章节
    if not os.path.exists("chapters"): return
    files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
    
    plot_history = []
    for file_name in files:
        print(f"正在读取 {file_name} 并提炼记忆...")
        with open(os.path.join("chapters", file_name), "r", encoding="utf-8") as f:
            content = f.read()
            
        # 让 AI 总结这一章
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": f"请用15字以内总结本章核心事件：\n{content[:2000]}"}]
        )
        summary = res.choices[0].message.content.strip().replace('"', '')
        plot_history.append(summary)

    # 2. 写回 JSON
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    data["plot_history"] = plot_history
    
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ 历史记忆全量补全完成！")

if __name__ == "__main__":
    heal_history()
