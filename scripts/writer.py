import os
import re
import sys
from openai import OpenAI

def get_context():
    if not os.path.exists("README.md"):
        return "请开始创作", "暂无规则"
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 更加灵活的正则：匹配包含“守则”或“法则”的标题
    rules_match = re.search(r"## .*?[守则|法则|世界观].*?\n(.*?)(?=\n##|$)", content, re.S)
    rules_text = rules_match.group(1).strip() if rules_match else "通用规则：保持冷静，利用空间。"
    return content, rules_text

def write_novel():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 错误：未在环境变量中找到 AI_API_KEY，请检查 GitHub Secrets 设置。")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    full_context, rules = get_context()
    branch_name = os.getenv("GITHUB_REF_NAME", "new_chapter")

    print(f"🚀 正在调用 DeepSeek 为分支 {branch_name} 生成番茄风格怪谈...")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system", 
                    "content": f"""你是一位番茄小说白金作家。文风要求：
                    1. 节奏极快，每段不超3行。
                    2. 大量留白，多对话，少描写。
                    3. 必须遵守规则：{rules}"""
                },
                {"role": "user", "content": f"当前设定：\n{full_context}\n\n请写出该分支的新章节内容。"}
            ]
        )
        
        content = response.choices[0].message.content
        
        # 保存文件
        os.makedirs("chapters", exist_ok=True)
        safe_filename = branch_name.replace("/", "_")
        file_path = f"chapters/{safe_filename}.md"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"✅ 章节已保存至：{file_path}")
        
    except Exception as e:
        print(f"❌ API 调用或保存失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
