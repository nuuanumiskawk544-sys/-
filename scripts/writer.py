import os
import re
import sys
import json
from openai import OpenAI

# ======= 核心配置区 =======
MAX_TOTAL_WORDS = 1500000  # 总字数熔断
CHAPTER_WORDS = 2000       # 每章目标字数
STORY_FILE = "四合院：我的空间能产肉，众禽馋疯了.txt"
OUTLINE_FILE = "四合院：我的空间能产肉，众禽馋疯了 大纲.txt"
MODEL_NAME = "deepseek-chat" 
STATE_FILE = "world_state.json"
# =========================

def get_comprehensive_context():
    """智能上下文识别：强制从第 15 章基准开始衔接"""
    outline, world_state_data, world_state_str = "暂无大纲", {}, "暂无实时状态记录"
    last_content = "暂无前情提要"
    
    # 🚨 【设定基准】初始章数为 15
    max_chapter_num = 15 

    # 1. 读取大纲
    if os.path.exists(OUTLINE_FILE):
        with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
            outline = f.read()

    # 2. 从 JSON 加载进度
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                world_state_data = json.load(f)
                # 确保不低于 15
                max_chapter_num = max(15, int(world_state_data.get("last_update_chapter", 15)))
        except: pass

    # 3. 物理扫描 chapters 文件夹纠偏
    found_in_folder = False
    if os.path.exists("chapters"):
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        if files:
            nums = [int(re.match(r'(\d+)', f).group(1)) for f in files if re.match(r'(\d+)', f)]
            if nums:
                folder_max = max(nums)
                if folder_max > max_chapter_num:
                    max_chapter_num = folder_max
            
            # 读取文件夹中最新一章的内容
            pattern = f"{max_chapter_num:03d}"
            target_files = [f for f in files if f.startswith(pattern)]
            if target_files:
                with open(os.path.join("chapters", target_files[0]), "r", encoding="utf-8") as f:
                    last_content = f.read()
                found_in_folder = True

    # 4. 【衔接逻辑】如果 chapters 没文件，读根目录原文 .txt 的末尾
    if not found_in_folder and os.path.exists(STORY_FILE):
        print(f"📖 chapters为空，正在从原文提取第 {max_chapter_num} 章末尾作为第 16 章的起点...")
        with open(STORY_FILE, "r", encoding="utf-8") as f:
            full_text = f.read()
            # 读取原文最后 2500 字作为续写依据
            last_content = full_text[-2500:]

    # 5. 构建状态字符串（包含前20章剧情黑名单以防重复）
    history = world_state_data.get("plot_history", [])
    history_summary = " -> ".join(history[-20:]) if history else "尚无记录"
    world_state_str = f"【已发生核心剧情（绝对严禁重复）】: {history_summary}\n"
    world_state_str += f"【当前人物状态】: {json.dumps(world_state_data.get('key_npcs', {}), ensure_ascii=False)}"

    return outline, world_state_str, last_content, max_chapter_num, world_state_data

def update_state_via_ai(client, new_chapter_content, old_data, current_chapter_num):
    """【绝不动摇的追加逻辑】强制读取物理文件，严禁 AI 篡改历史"""
    print(f"🧠 正在分析第 {current_chapter_num} 章并存入长效记忆库...")

    # 🚨 【修正后的第二步：加入严格 Prompt 约束】
    # 强制要求 AI 只能输出本章进展，禁止复述设定或历史
    summary_prompt = f"""
    分析新生成的第 {current_chapter_num} 章，仅提取一个核心剧情进展。
    
    要求（违者扣分）：
    1. 严禁包含任何“核心设定”、“系统介绍”、“金手指描述”等废话。
    2. 严禁复述前情提要。
    3. 只返回本章发生的新动作，字数在15字以内。
    4. 示例：林东来在街道办通过考核，成功为苏云秀入职。
    
    格式要求：必须返回 JSON 格式，如 {{"summary": "一句话描述"}}
    
    【待分析内容】: 
    {new_chapter_content[:2500]}
    """
    try:
        # 获取 AI 提炼的新摘要
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": summary_prompt}],
            response_format={ "type": "json_object" }
        )
        res_json = json.loads(response.choices[0].message.content)
        new_summary_text = res_json.get("summary", "剧情继续推进")

        # 2. 【核心保命逻辑】强制从硬盘读取最真实的历史
        # 不要信任内存里的 old_data，因为它可能被上一步逻辑洗掉了
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                # 这一步是读取硬盘上所有 1-18 章的真实历史
                disk_data = json.load(f)
        else:
            # 如果文件离奇失踪，才创建一个空的模板
            disk_data = {"plot_history": [], "last_update_chapter": 0}

        # 确保 plot_history 始终是一个列表，防止被 AI 篡改为字符串
        if not isinstance(disk_data.get("plot_history"), list):
            disk_data["plot_history"] = []

        # 3. 【防重逻辑】构造带编号的条目
        new_entry = f"第{current_chapter_num}章：{new_summary_text}"
        
        # 检查是否已经存在该章节记录，不存在才追加
        if not any(entry.startswith(f"第{current_chapter_num}章") for entry in disk_data["plot_history"]):
            disk_data["plot_history"].append(new_entry)
            print(f"✅ 已成功将第 {current_chapter_num} 章追加到末尾。")
        else:
            print(f"⚠️ 第 {current_chapter_num} 章已在记录中，跳过追加以防重复。")

        # 4. 更新章节进度（只更新数字，不准 AI 修改其他字段）
        disk_data["last_update_chapter"] = current_chapter_num

        # 5. 【物理写入】用合并后的 disk_data 覆盖写入，这才是真正的追加
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(disk_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        print(f"🚀 物理同步成功！当前记忆总条数: {len(disk_data['plot_history'])}")

    except Exception as e:
        print(f"❌ 同步失败，原因: {str(e)}")
# ======= 执行主逻辑 =======
def main():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 未找到 AI_API_KEY")
        return
        
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 1. 获取所有上下文和当前章数
    outline, world_state_str, last_content, max_num, old_data = get_comprehensive_context()
    
    # 2. 计算新章编号（15 + 1 = 16）
    next_num = max_num + 1
    print(f"🚀 准备开始创作第 {next_num} 章...")

    # [这里插入你调用 AI 生成文章的具体代码，假设结果存入 new_chapter_content]
    # new_chapter_content = ... 
    
    # 3. 生成后同步状态
    # update_state_via_ai(client, new_chapter_content, old_data, next_num)

if __name__ == "__main__":
    main()

def write_novel():
    outline, world_state_str, last_context, current_count, old_state_data = get_comprehensive_context()
    next_index = current_count + 1
    
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 错误：未配置 AI_API_KEY")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 5. 构建核心 Prompt
    prompt = f"""
    你现在是一名拥有十年经验的网文白金作家,擅长写《四合院》同人爽文。
    精通“三番四震”、“大循环套小循环”等所有爆款网文技巧。

    【创作铁律】：
    1. 极致爽感：核心是情绪拉扯和打脸反转，爽点要密集且层层递进。
    2. 强力钩子：每章结尾必须有让人欲罢不能的悬念或期待。
    3. 高质量：拒绝重复剧情、无效对话和扁平的工具人配角。
    4. 节奏为王：剧情推进张弛有度，完美承接前文，逻辑严谨。
    【指令】
    1. 如果描写林东来在院子里偷偷使用系统产物做饭，香味要穿透窗户，让四合院禽兽们家里吃窝窝头都咽不下去。
    2. 如果描写贾张氏在门外骂街，增加其心理活动描写。
    3. 描写副食店的排队场景。
    4. 要强调年代里粮票的珍贵。
    5. 突出大院里那种压抑的邻里监视感。
    6. 增加对食物香气和口感的细节描写，要写出那种在物资匮乏年代，肉香飘满全院，馋得棒梗流哈喇子、小当哭闹的画面感。
    7. 压抑后爆发的要求：前1/3篇幅描写禽兽的嚣张和道德绑架，后2/3篇幅描写主角的无情反击，回扣要狠，不留余地。
    8.注入“京味儿”方言：台词中多加入“爷们儿”、“没跑儿”、“不吝”、“拿大顶”等地道老北京话，增加时代代入感。
    9.避免多次使用“AI生成感”强烈的短语（例如“嘴角勾起一抹XX的弧度”、“空气仿佛凝固了”，死寂，寂静，疯狂，涟漪，好像，仿佛，凝固，重锤，毒蛇，取而代之，不易察觉，死一般，沉重，凝滞，铁锤，天雷，淬了毒，淬了冰，丝滑，然而，随之而来，不可避免，浓得化不开, 丝丝缕缕,仿佛/如同、深吸一口气、前所未有，繁复的, 狰狞又华贵, 沉甸甸的, 一片混沌, 枯槁的, 空荡荡的, 不甘和威严, 深沉如渊, 嗡的一声, 五味杂陈, 冰冷的机械音, 毫无征兆地, 神清气爽, 踉跄一步, 突兀, 大脑宕机, 连滚带爬, 面面相觑, 精光一闪而过，浓重的, 繁复的, 突兀地, 毫无感情的, 戛然而止，轰、炸开、就像是、嘴角勾起、取而代之的是、顿时、紧锁、立刻、连忙、显然、似乎、虽然、大致、确实、几乎、可能、注定、接下来、渐渐、更是、一定、或许、十分、沉重、看不出、淡淡、郑重、此刻、恐怕、清淡、不知道、似乎、心中一凛、眼中闪过一丝惊讶、行云流水、心下了然、话锋一转、眼神深邃、显著、至关重要、微微挑眉、波涛汹涌、绝对、不可估量、仿佛、随时、无法想象、无法用言语形容、此刻、显然、脸上带着笑意、平静地、显得有些兴奋、心中了然、激动地、眼神热切、目光里毫不遮掩、淡淡地、不卑不亢、仿佛，如同、可能、显得异常清晰、暂时、他/她知道、像是、不断、像、瞬间、这一刻、再次、嘴角勾起一抹、一时之间、这一次、看似、微微挑眉、沉吟、隐隐有了猜测、心中了然、淡淡地应了一句、不卑不亢、目光扫过、心中一片平静、显得更加……、知道、一丝、坚定、xx的眼神、深吸一口气、缓缓地说、锐利的眼睛、他的嘴角微微上扬、他的表情变暗、他的心一跳、他的脸变了、不容置疑、嘴角、脸色、不易察觉、的目光、心中、觉得、意识到、感觉到、认为、一抹、一股、似乎、些许、有点、略微、带着...、猛地、口吻、纯粹、冰冷、电弧、闪烁、裹挟、清冷、沸腾、郑重、扭曲、撕裂、漆黑、窒息、剧痛、心中一动、不动声色、小心翼翼、沉吟片刻、心里隐隐有了猜测、我知道、果然、脸上堆满了笑、像淬了毒的匕首、刺入……的心脏、嘴角勾起一个……的弧度、……看得目瞪口呆、嘴巴张得能塞下一个鸡蛋、却比……还要冰冷、像在看一个……的人、透露出的寒意、让空气的温度都下降了几度、声音不大，却……、声音平静、却重重砸在……的心头、时间仿佛被按下了暂停、带着一丝、声音坚定、眼神坚定、眼神锐利、不可置信、不可置疑、仿佛、如同、指节泛白、空气凝滞如铁、死寂、沉寂、以一种、他知道、这不是……而是、只是、冷寂、眼中流露出……的表情、我都要烦死了、声音轻细，却重重砸在……的心头、时间仿佛被按下了暂停、我知道，我赢了、如同、好像、似乎、充满、带着一丝、以及、声音坚定、眼神坚定、眼神锐利、不可置信、不可置疑、嘴角勾起一抹弧度、仿佛、如同、指节泛白、一丝、在……炸开、带着不容置疑的……、声音不大、炸雷、炸开 精准地 僵住了 凝固 甜腻 扯出 力道大得惊人 闷响 诅咒 冰凉 宣战 近乎偏执 巨大、彻底、像一台精密的仪器、无法形容、）。
    10.在与女主及暧昧对象或年轻漂亮的女性互动时增加雪白内容描写及叙事。
    11.对四合院内众禽兽打脸或反击侵犯自己权益时不使用系统的情况下多用“以其人之道还治其人之身”，“以势压人”的办法。
    12.可以增加“屎尿屁”的禽兽恶心男女主方式，男女主整治打脸方式也可使用“屎尿屁”的方式。
    【雪白内容描写设定】：
    1.视觉暗示：穿着或动作挑逗、但未涉及敏感部位或明确色情。
    2.语言暖味：使用双关、暗示性强的语言。引人遐想但不直接描述。
    3.情节设计：营造“似是而非”的氛围，比如角色关系、剧情冲突有暖昧空间。
    4.标题诱导：使用具有争议或刺激性的标题吸引点击，内容则相对克制。边界模糊：利用规则未明确定义的模糊区域规避处罚。
    5.增加对女主的外貌身材的擦边描写。
    6.增加男主细腻的心理描写。
    7.增加男女主之间的暧昧的对白和动作互动描写。
    8.增加男主占女主便宜的动作和语言。
    9.男女主感情循序渐进。
    10.边界模糊：利用规则未明确定义的模糊区域规避处罚。
    【大纲设定】：
    {outline}
    【当前世界/人物实时状态卡】：（请严格遵守此设定，不要产生逻辑冲突）
    {world_state_str}
    【前情提要（上一章结尾）】：
    {last_context[-1200:]}
    【核心续写要求】：
    1. 严禁重复！ 禁止重复写上一章已经出现的动作、对话或环境描写。
    2. 瞬间接棒： 请直接从上一章最后一个动作或最后一句话之后开始写，不要做任何过渡性的回顾或总结。
    3. 杜绝废话： 每一章开头严禁描写天气、院子全景或重复介绍系统属性，直接进入新的矛盾冲突。
    4. 逻辑校验： 如果上一章主角在吃饭，这一章要么接着吃，要么吃完起身，动作必须连贯。
    【创作任务】：
    请接续前情，创作第 {next_index} 章。

    【写作要求】：
    1. 章节标题格式为：“第{next_index}章：[具体标题]”。
    2. 文风要求：富有60年代京味儿，多用口语对话，节奏极快。
    3. 性格准则：主角林东来腹黑冷酷，绝对不圣母；众禽（贾张氏、易中海等）必须表现出极度的贪婪和被主角碾压后的挫败感。
    4. 核心要素：必须有“怨气值”收集的描写，以及主角利用金手指（空间肉食、灵泉）改善生活的描写。
    5. 字数要求：不少于 {CHAPTER_WORDS} 字。

    【绝对禁令】：
    1. 严禁重复描写：当前已进行到第 {next_index} 章。禁止再写林东来刚穿越、刚获得系统、刚分家、刚遇到贾张氏第一次撒泼等前 3 章剧情！
    2. 进度锚点：当前剧情已经发展到：{world_state_str}。
    3. 强制推进：本章必须发生新的冲突（例如：鸽子市交易、厂里升职、或者苏云秀救治后的互动）。
    4. 绝对严禁写上述“已发生剧情”中的任何桥段！
    5. 绝对严禁写穿越初期、分家、第一次见贾张氏等旧事！
    6. 如果历史记录显示苏云秀已被救，本章严禁再写救人，应写后续互动。
    【避雷针】：严禁重复第*章的[某具体情节]和第*章的[某具体情节]。如果本章剧情与历史记录雷同，系统将判定为失败。请开启全新冲突！
    【前情提要（仅供接棒，严禁复述）】：
    {last_context[-1500:]}
    
    请直接从上一章结尾的动作开始，不要回顾，不要总结，直接写新剧情！
    """

    print(f"🚀 正在调用 AI 生成第 {next_index} 章...")

    try:
        # 3. 先通过 AI 生成新章节内容
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

        # 4. 根据生成的内容动态确定文件名 (解决 UnboundLocalError)
        os.makedirs("chapters", exist_ok=True)
        title_match = re.search(r'第\d+章[：\s]*(.*)\n', new_chapter_content)
        if title_match:
            clean_title = re.sub(r'[\\/:*?"<>|]', '', title_match.group(1).strip())
        else:
            clean_title = "新进展"
            
        file_name = f"{next_index:03d}_{clean_title[:10]}.md"
        file_path = os.path.join("chapters", file_name)

        # 5. 【第一步写入】物理保存生成的章节
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_chapter_content)
        print(f"✅ 章节已保存: {file_path}")

        # 6. 【第二步写入】实时更新人物状态卡 (world_state.json)
        # 🚨 只有在这里调用，AI 才能根据刚刚生成的 new_chapter_content 来更新 JSON！
        update_state_via_ai(client, new_chapter_content, old_state_data, next_index)

    except Exception as e:
        print(f"❌ 运行过程中出错：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
