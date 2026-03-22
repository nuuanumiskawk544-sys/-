import os
import re
import sys
from openai import OpenAI

# ======= 核心配置区 =======
MAX_TOTAL_WORDS = 1500000  # 总字数熔断
CHAPTER_WORDS = 2000      # 每章目标字数
STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了.txt"
OUTLINE_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt"
MODEL_NAME = "deepseek-chat" # 或使用你指定的模型
# =========================

def get_comprehensive_context():
    """
    智能上下文识别：
    1. 扫描 chapters 目录，寻找文件名开头数字最大的文件。
    2. 如果 chapters 为空，扫描原始 txt 文件提取最后一章编号。
    """
    outline = "暂无大纲"
    if os.path.exists(OUTLINE_FILE):
        with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
            outline = f.read()

    last_content = ""
    max_chapter_num = 0

    # 优先检查自动化生成的章节目录
    if os.path.exists("chapters"):
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        if files:
            chapter_nums = []
            for f in files:
                # 匹配文件名开头的数字，如 "017_标题.md" -> 17
                match = re.match(r'(\d+)', f)
                if match:
                    chapter_nums.append(int(match.group(1)))
            
            if chapter_nums:
                max_chapter_num = max(chapter_nums)
                # 找到该编号对应的完整文件名
                pattern = f"{max_chapter_num:03d}"
                target_files = [f for f in files if f.startswith(pattern)]
                if target_files:
                    with open(os.path.join("chapters", target_files[0]), "r", encoding="utf-8") as f:
                        last_content = f.read()
                    print(f"📡 检测到 chapters 最新进度：第 {max_chapter_num} 章")

    # 如果 chapters 没东西，则读取原始 txt 文档
    if max_chapter_num == 0 and os.path.exists(STORY_FILE):
        with open(STORY_FILE, "r", encoding="utf-8") as f:
            full_text = f.read()
            # 提取最后一段内容作为 AI 的“前情提要”
            last_content = full_text[-2000:] 
            # 正则匹配最后出现的“第XX章”
            # 兼容“第 16 章”、“第16章”、“【第16章】”等格式
            chapter_matches = re.findall(r'第\s*(\d+)\s*章', full_text)
            if chapter_matches:
                max_chapter_num = int(chapter_matches[-1])
                print(f"📖 检测到原始文档最新进度：第 {max_chapter_num} 章")

    return outline, last_content, max_chapter_num

def write_novel():
    # 1. 获取上下文和当前章节数
    outline, last_context, current_count = get_comprehensive_context()
    
    # 2. 确定下一章编号
    next_index = current_count + 1
    
    # 保底逻辑：如果识别出的章节数异常（比如你确定要从17开始）
    # 可取消下面一行的注释强制修正：
    # if next_index < 17: next_index = 17

    # 3. 初始化 AI 客户端
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 错误：未配置 AI_API_KEY 环境变量")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 4. 构建 Prompt
    prompt = f"""
你现在是一名拥有十年经验的网文白金作家，擅长写《四合院》同人爽文。

【大纲设定】：
{outline}

【前情提要（上一章结尾）】：
{last_context[-1500:]}

【创作任务】：
请接续前情，创作第 {next_index} 章。

【写作要求】：
1. 章节标题格式为：“第{next_index}章：[具体标题]”。
2. 文风要求：富有60年代京味儿，多用口语对话，节奏极快。
3. 性格准则：主角林东来腹黑冷酷，绝对不圣母；众禽（贾张氏、易中海等）必须表现出极度的贪婪和被主角碾压后的挫败感。
4. 核心要素：必须有“怨气值”收集的描写，以及主角利用金手指（空间肉食、灵泉）改善生活的描写。
5. 字数要求：不少于 {CHAPTER_WORDS} 字。

直接开始正文：
"""

    print(f"🚀 正在调用 AI 生成第 {next_index} 章...")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一名冷酷爽文风格的网文作家，严禁圣母情节。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            stream=False
        )

        new_chapter_content = response.choices[0].message.content

        # 5. 保存文件
        os.makedirs("chapters", exist_ok=True)
        
        # 尝试从内容中提取 AI 给的标题
        title_match = re.search(r'第\d+章：(.*)\n', new_chapter_content)
        if title_match:
            clean_title = re.sub(r'[\\/:*?"<>|]', '', title_match.group(1).strip())
        else:
            clean_title = "新章节"
            
        file_name = f"{next_index:03d}_{clean_title[:10]}.md"
        file_path = os.path.join("chapters", file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_chapter_content)

        print(f"✅ 成功生成：{file_path}")

    except Exception as e:
        print(f"❌ AI 生成过程中出错：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
