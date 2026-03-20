import os
import re
from openai import OpenAI

def get_context():
    """
    从 README.md 提取规则和设定。
    脚本会寻找 '## 📜 幸存者守则' 这一行下方的文字。
    """
    if not os.path.exists("README.md"):
        return "请开始恐怖怪谈创作", "暂无生存规则"
    
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 使用正则匹配 '## 📜 幸存者守则' 到下一个标题之间的内容
    rules_match = re.search(r"## 📜 幸存者守则\n(.*?)(?=\n##|$)", content, re.S)
    rules_text = rules_match.group(1).strip() if rules_match else "暂无规则约束"
    
    return content, rules_text

def validate_logic(content):
    """
    逻辑审查：检查 AI 是否在章节中违反了 README 里的硬性规定。
    你可以根据自己的设定在这里增加更多的关键词检查。
    """
    errors = []
    # 示例 1：如果在14层睁眼，直接报错
    if "14层" in content and "睁开眼" in content:
        errors.append("违反禁忌：在14层睁眼了")
    
    # 示例 2：不能与红衣人交流
    if "红衣" in content and ("交流" in content or "说话" in content or "对话" in content):
        errors.append("违反禁忌：与红衣人交流了")
        
    return errors

def write_novel():
    # 1. 初始化 DeepSeek 客户端（通过环境变量读取 API Key）
    # 这里的 base_url 已经适配 DeepSeek
    client = OpenAI(
        api_key=os.getenv("AI_API_KEY"), 
        base_url="https://api.deepseek.com" 
    )
    
    # 获取 README 里的上下文和规则
    full_context, rules = get_context()
    # 获取当前 GitHub 分支名，作为章节标识
    branch_name = os.getenv("GITHUB_REF_NAME", "new_chapter")

    print(f"🚀 正在为分支 {branch_name} 生成番茄风格怪谈内容...")

    # 2. 调用 AI 生成（注入番茄小说爆款文风提示词）
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system", 
                "content": f"""你是一位番茄小说网的顶级作家，擅长规则怪谈和系统空间流。
                
                【文风要求】：
                1. 节奏极快，每一句尽量不超过20字。
                2. 每一段不超过3行，多留白，方便手机阅读。
                3. 擅长在章末留悬念（钩子）。
                4. 严禁大量心理描写，多写对话、动作和环境的阴冷感。
                
                【必须遵守的规则约束】：
                {rules}"""
            },
            {
                "role": "user", 
                "content": f"当前小说背景：\n{full_context}\n\n请写出名为《{branch_name}》的新章节。要求文风阴冷、惊悚，字数控制在1500字左右。"
            }
        ]
    )
    
    content = response.choices[0].message.content

    # 3. 逻辑自检
    errors = validate_logic(content)
    if errors:
        # 如果违规，在正文顶部标注，方便你回炉重造
        content = f"⚠️ 【逻辑审查警报】：本章可能违反了以下规则：{errors}\n\n" + content
        print(f"❌ 逻辑校验未通过: {errors}")
    else:
        print("✅ 逻辑校验通过！")
    
    # 4. 自动保存到 chapters 文件夹
    os.makedirs("chapters", exist_ok=True)
    # 将分支名里的斜杠替换掉，防止路径报错
    safe_filename = branch_name.replace("/", "_")
    file_path = f"chapters/{safe_filename}.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✨ 章节已成功保存至：{file_path}")

if __name__ == "__main__":
    write_novel()
