import os
import re
import sys
from openai import OpenAI

# ======= 自定义配置区 =======
MAX_TOTAL_WORDS = 2500000  # 
CHAPTER_WORDS = 2000      # 
# ===========================

def get_total_word_count():
    """计算已生成章节的总字数"""
    if not os.path.exists("chapters"):
        return 0
    total = 0
    for file in os.listdir("chapters"):
        if file.endswith(".md"):
            with open(f"chapters/{file}", "r", encoding="utf-8") as f:
                total += len(f.read())
    return total

def get_config():
    if not os.path.exists("README.md"):
        return "规则怪谈", "保持警惕"
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    rules = re.search(r"## .*?[守则|法则|规则].*?\n(.*?)(?=\n##|$)", content, re.S)
    return content, rules.group(1).strip() if rules else "遵守规则"

def get_last_chapter():
    if not os.path.exists("chapters") or not os.listdir("chapters"):
        return "开始第一章", 0
    files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
    with open(f"chapters/{files[-1]}", "r", encoding="utf-8") as f:
        return f.read(), len(files)

def write_novel():
    # 1. 字数限制检查
    current_total = get_total_word_count()
    if current_total >= MAX_TOTAL_WORDS:
        print(f"🛑 已达到总字数限制 ({current_total}/{MAX_TOTAL_WORDS})。小说正式完结！")
        sys.exit(0)

    client = OpenAI(api_key=os.getenv("AI_API_KEY"), base_url="https://api.deepseek.com")
    full_context, rules = get_config()
    last_content, count = get_last_chapter()
    next_index = count + 1

    print(f"✍️ 当前总字数: {current_total}，正在创作第 {next_index} 章...")

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user", 
                "content": f"你是番茄小说作家。前情：{last_content[-600:]}\n规则：{rules}\n请写第{next_index}章，字数{CHAPTER_WORDS}左右。首行格式：第XX章：标题。"
            }]
        )
        new_content = response.choices[0].message.content
        
        # 提取标题存文件
        first_line = new_content.split('\n')[0]
        title = re.sub(r'[^\w\s-]', '', first_line).strip().replace(' ', '_')
        
        os.makedirs("chapters", exist_ok=True)
        file_path = f"chapters/{next_index:03d}_{title}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ 完成：{file_path}")
    except Exception as e:
        print(f"❌ 失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
