import os
import re
import sys
from openai import OpenAI

def get_config():
    """获取 README 中的全局设定和规则"""
    if not os.path.exists("README.md"):
        return "规则怪谈", "暂无规则"
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    rules_match = re.search(r"## .*?[守则|法则|规则].*?\n(.*?)(?=\n##|$)", content, re.S)
    rules = rules_match.group(1).strip() if rules_match else "保持冷酷，遵守规则。"
    return content, rules

def get_last_chapter():
    """读取最后一章的内容，让 AI 知道剧情进度"""
    if not os.path.exists("chapters") or not os.listdir("chapters"):
        return "这是第一章，请开始故事。", 0
    
    files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
    last_file = files[-1]
    with open(f"chapters/{last_file}", "r", encoding="utf-8") as f:
        return f.read(), len(files)

def write_novel():
    client = OpenAI(api_key=os.getenv("AI_API_KEY"), base_url="https://api.deepseek.com")
    full_context, rules = get_config()
    last_content, count = get_last_chapter()
    next_index = count + 1

    print(f"🚀 正在构思第 {next_index} 章...")

    prompt = f"""
    你是番茄小说白金作家，擅长中式规则怪谈。
    【前情提要】：{last_content[-500:]} # 取最后500字防止Token溢出
    【全局规则】：{rules}
    
    【任务】：
    1. 为第 {next_index} 章起一个带有悬念的标题。
    2. 按照番茄风（短句、多留白、快节奏）续写本章内容。
    3. 字数 1500 字左右。
    4. 格式要求：第一行必须是“第XX章：标题名”，然后空两行开始正文。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )
        new_content = response.choices[0].message.content
        
        # 自动提取 AI 起的标题作为文件名
        first_line = new_content.split('\n')[0]
        title = re.sub(r'[^\w\s-]', '', first_line).strip().replace(' ', '_')
        
        os.makedirs("chapters", exist_ok=True)
        file_path = f"chapters/{next_index:03d}_{title}.md" # 格式如 002_第2章_诡异的镜子.md
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"✅ 第 {next_index} 章创作完成：{file_path}")
    except Exception as e:
        print(f"❌ 创作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
