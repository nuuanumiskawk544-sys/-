import os
import re
from openai import OpenAI

def get_context():
    if not os.path.exists("README.md"):
        return "请开始创作", "暂无规则"
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 强化正则：即便你没加表情符号，或者标题写错了，它也不会崩溃
    rules_match = re.search(r"## .*守则\n(.*?)(?=\n##|$)", content, re.S)
    if not rules_match:
        # 如果找不到“守则”标题，就抓取全文，防止程序报错
        return content, "通用怪谈规则：保持警惕，利用空间。"
    
    return content, rules_match.group(1).strip()

def write_novel():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 错误：未在环境变量中找到 AI_API_KEY")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    full_context, rules = get_context()
    branch_name = os.getenv("GITHUB_REF_NAME", "new_chapter")

    print(f"🚀 正在调用 DeepSeek 生成内容...")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"番茄小说风格，节奏快。规则：{rules}"},
                {"role": "user", "content": f"基于设定写新章节：{full_context}"}
            ]
        )
        # 保存逻辑... (同之前)
        os.makedirs("chapters", exist_ok=True)
        with open(f"chapters/{branch_name.replace('/', '_')}.md", "w", encoding="utf-8") as f:
            f.write(response.choices[0].message.content)
        print("✅ 生成成功！")
    except Exception as e:
        print(f"❌ 调用 API 失败: {e}")

if __name__ == "__main__":
    write_novel()
