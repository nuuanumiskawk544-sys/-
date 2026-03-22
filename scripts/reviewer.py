import os
import sys

# ======= 审稿标准配置 =======
MIN_WORDS = 1200          # 最小字数
MUST_NOT_HAVE = ["原谅", "大方送肉", "和解", "微信", "手机", "电脑"] # 绝对违禁词
PROTAGONIST_NAME = "林东来"

def review_chapter(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    report = []
    is_passed = True

    # 1. 字数检查
    word_count = len(content)
    if word_count < MIN_WORDS:
        report.append(f"❌ 字数不足: 当前{word_count}字，要求至少{MIN_WORDS}字。")
        is_passed = False

    # 2. 违禁词/圣母倾向检查
    for word in MUST_NOT_HAVE:
        if word in content:
            report.append(f"❌ 检测到违禁词或人设崩坏: '{word}'")
            is_passed = False

    # 3. 角色档案匹配 (示例：确保主角没变圣母)
    if "心软" in content or "算了" in content and PROTAGONIST_NAME in content:
        report.append(f"⚠️ 疑似出现圣母情节，请人工核查主角情绪。")
        # 这里可以设定为不阻断，但记录日志

    # 4. 自动修正（静默处理）
    content = content.replace("手机", "步话机").replace("微信", "写信")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return is_passed, report

def run():
    if not os.path.exists("chapters"):
        return
    
    files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
    if not files:
        return
        
    latest_file = os.path.join("chapters", files[-1])
    print(f"🧐 正在审阅：{files[-1]}...")
    
    passed, reports = review_chapter(latest_file)
    
    for r in reports:
        print(r)
        
    if not passed:
        print("🚫 审稿未通过，该章节已作废，不会同步到仓库。")
        sys.exit(1) # 退出码 1 会阻断后续的 Git Push
    else:
        print("✅ 审稿通过！准备发布。")

if __name__ == "__main__":
    run()

def update_world_state(chapter_content, chapter_num):
    """
    调用 AI 总结本章，更新 world_state.json
    """
    api_key = os.getenv("AI_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    with open("world_state.json", "r", encoding="utf-8") as f:
        old_state = f.read()

    summary_prompt = f"""
    你是一个文学编辑。请根据【新章节内容】，更新【旧世界状态】。
    要求：
    1. 保持简练，每条信息不超过30字。
    2. 更新主角的最新物资、NPC的好感度或死活。
    3. 给出最新的剧情进度总结。
    
    【旧世界状态】：{old_state}
    【新章节内容】：{chapter_content[:2000]}
    
    请直接返回更新后的 JSON 格式，不要有其他废话。
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": summary_prompt}],
            response_format={ 'type': 'json_object' } # 强制返回 JSON
        )
        new_state = response.choices[0].message.content
        with open("world_state.json", "w", encoding="utf-8") as f:
            f.write(new_state)
        print("📊 人物状态卡已同步更新。")
    except:
        print("⚠️ 状态更新失败，跳过。")
