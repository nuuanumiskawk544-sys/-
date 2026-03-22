import os
import re
import sys
from openai import OpenAI

# ======= 核心配置区 =======
MAX_TOTAL_WORDS = 500000  # 总字数熔断
CHAPTER_WORDS = 2000      # 每章目标字数
STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了.txt" # 你的原始文档名
OUTLINE_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt" # 大纲文件名
# =========================

def get_comprehensive_context():
    """读取大纲和已有内容的最末尾，构建最强上下文"""
    outline = ""
    if os.path.exists(OUTLINE_FILE):
        with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
            outline = f.read()

    # 优先读取 chapters 文件夹里的新章节，如果没有，读取原始 txt
    last_content = ""
    chapter_count = 0
    
    if os.path.exists("chapters") and os.listdir("chapters"):
        files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
        chapter_count = len(files)
        with open(f"chapters/{files[-1]}", "r", encoding="utf-8") as f:
            last_content = f.read()
    elif os.path.exists(STORY_FILE):
        with open(STORY_FILE, "r", encoding="utf-8") as f:
            full_text = f.read()
            # 简单粗暴提取最后 1500 字作为参考
            last_content = full_text[-1500:]
            # 尝试通过“第XX章”匹配当前章节数
            chapters = re.findall(r'第(\d+)章', full_text)
            chapter_count = int(chapters[-1]) if chapters else 0

    return outline, last_content, chapter_count

def write_novel():
    outline, last_context, current_count = get_comprehensive_context()
    next_index = current_count + 1
    
    client = OpenAI(api_key=os.getenv("AI_API_KEY"), base_url="https://api.deepseek.com")

    # 构造针对性极强的 Prompt
    prompt = f"""
    你现在是顶尖网文作家，正在续写四合院题材小说。
    
    【核心大纲参考】：
    {outline}
    
    【前情提要】：
    {last_context}
    
    【创作要求】：
    1. 当前章节：第{next_index}章。
    2. 文风要求：行文要有60年代京味儿，台词要泼辣、有生活气息。
    3. 角色性格：林东来果断狠辣、不圣母；众禽（易中海、贾张氏、秦淮茹等）贪婪且虚伪。
    4. 爽点：必须包含“打脸”或“物质碾压”情节。
    5. 格式：第一行为“第{next_index}章：标题”，后续直接开始正文，字数要求{CHAPTER_WORDS}字。
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一名擅长写《四合院》同人文的资深网文作家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7 # 保持一定的创作随机性
        )
        
        new_content = response.choices[0].message.content
        os.makedirs("chapters", exist_ok=True)
        
        # 提取标题作为文件名
        title_match = re.search(r'第\d+章：(.*)\n', new_content)
        title = title_match.group(1).strip() if title_match else "新章节"
        file_path = f"chapters/{next_index:03d}_{title[:10]}.md"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ 第 {next_index} 章创作完成：{file_path}")
        
    except Exception as e:
        print(f"❌ 创作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
