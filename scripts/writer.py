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
    """智能上下文识别：强制识别本地 chapters 文件夹的最高编号"""
    outline, world_state_data, world_state_str = "暂无大纲", {}, "暂无实时状态记录"
    last_content, max_chapter_num = "暂无前情提要", 0

    # 1. 读取大纲
    if os.path.exists(OUTLINE_FILE):
        with open(OUTLINE_FILE, "r", encoding="utf-8") as f:
            outline = f.read()

    # 2. 【核心步骤】识别 chapters 文件夹中的最高章节编号
    if os.path.exists("chapters"):
        # 获取所有 .md 文件
        files = [f for f in os.listdir("chapters") if f.endswith(".md")]
        if files:
            # 🚨 关键：使用正则表达式提取文件名开头的数字（如 "018_Chapter.md" -> 18）
            nums = []
            for f in files:
                match = re.match(r'(\d+)', f)
                if match:
                    nums.append(int(match.group(1)))
            
            if nums:
                max_chapter_num = max(nums) # 找到最大的数字，比如 17
                print(f"📡 [DEBUG] 脚本物理扫描完成：当前已写到第 {max_chapter_num} 章")
                
                # 找到对应这个最大数字的文件，读取内容作为“前情提要”
                pattern = f"{max_chapter_num:03d}" # 格式化为 017 这种形式
                target_files = [f for f in files if f.startswith(pattern)]
                if target_files:
                    target_path = os.path.join("chapters", target_files[0])
                    with open(target_path, "r", encoding="utf-8") as f:
                        last_content = f.read()
            else:
                print("⚠️ [WARNING] chapters 文件夹里有文件，但没找到数字编号。")
        else:
            print("ℹ️ [INFO] chapters 文件夹为空，准备从第 1 章开始。")

    # 3. 读取状态卡 (world_state.json)
if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                world_state_data = json.load(f)
                # --- 新增：提取历史剧情去重索引 ---
                history_list = world_state_data.get("plot_history", [])
                history_summary = " -> ".join(history_list[-20:]) if history_list else "尚无记录"
                
                # 重新构建发给 AI 的状态字符串
                world_state_str = f"【绝对禁写-已发生剧情轨迹】: {history_summary}\n"
                world_state_str += f"主角状态: {world_state_data.get('protagonist', '未知')}\n"
                world_state_str += "关键人物现状:\n" + "\n".join([f"- {k}: {v}" for k, v in world_state_data.get('key_npcs', {}).items()])
                world_state_str += f"\n当前物资储备: {world_state_data.get('current_inventory', '未知')}"
                world_state_str += f"\n剧情进度总结: {world_state_data.get('plot_progress', '未知')}"
        except Exception as e:
            print(f"❌ [ERROR] 读取状态文件失败: {e}")

    return outline, world_state_str, last_content, max_chapter_num, world_state_data

def update_state_via_ai(client, new_chapter_content, old_data):
    """
    强制 AI 根据新剧情解析出人物状态的变化（如：林东来救了人、易中海破防了等）
    """
    print("🧠 正在实时分析剧情，更新人物状态卡...")
    
    # 构造极其严厉的 Prompt，防止 AI 偷懒返回旧数据

    update_prompt = f"""
    你现在是高能数据记录员。根据新章节内容，更新《四合院》世界状态 JSON。
    
    【更新要求】：
    1. 必须在 'plot_history' 数组中追加本章核心事件简述（严禁超过15字，如：林东来胡同救苏云秀）。
    2. 必须更新 'plot_progress'（描述当前主角的具体位置和动作）。
    3. 必须更新 'key_npcs'（根据剧情更新人物好感度或现状）。
    4. 必须更新 'last_update_chapter' 为 {int(old_data.get('last_update_chapter', 0)) + 1}。
    
    【旧数据】：{json.dumps(old_data, ensure_ascii=False)}
    【新情节】：{new_chapter_content[:1500]}
    直接返回 JSON 格式，不要废话。
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": update_prompt}],
            response_format={ "type": "json_object" } # 强制输出合法 JSON
        )
        
        # 解析并清理数据
        res_json = response.choices[0].message.content
        new_data = json.loads(re.search(r'\{.*\}', res_json, re.DOTALL).group())
        
        # 物理写入：确保文件被真正修改
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno()) # 强制同步到磁盘
            
        print(f"✨ 状态卡已更新！当前剧情位置：{new_data.get('plot_progress')}")
        
    except Exception as e:
        print(f"❌ 状态实时同步失败: {e}")

def write_novel():
    outline, world_state_str, last_context, current_count, old_state_data = get_comprehensive_context()
    next_index = current_count + 1
    
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("❌ 错误：未配置 AI_API_KEY")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 4. 构建核心 Prompt
    prompt = f"""
你现在是一名拥有十年经验的网文白金作家，擅长写《四合院》同人爽文。精通“三番四震”、“大循环套小循环”等所有爆款网文技巧。
【创作铁律】：
极致爽感： 核心是情绪拉扯和打脸反转，爽点要密集且层层递进。
强力钩子： 每章结尾必须有让人欲罢不能的悬念或期待。
高质量： 拒绝重复剧情、无效对话和扁平的工具人配角。
节奏为王： 剧情推进张弛有度，完美承接前文，逻辑严谨。
【指令】：
1. 苏云秀必须在指定章节前（第26章）登场，她要表现得极其可怜但眼神坚定。
2. 描写林东来在院子里煮“灵泉鸡汤”，香味要穿透窗户，让易中海家吃窝窝头都咽不下去。
3. 增加贾张氏在门外骂街的心理活动描写。
4. 特定要求：林东来早起签到获得灵泉灌溉技术。清晨去厂里的路上，在鸽子市附近的胡同口遇到饿晕的苏云秀，林东来利用21世纪的急救常识和空间井水救人，开启第一段温情线。要求文风保持冷峻，主角救人是出于系统任务或直觉，拒绝圣母心大发。直到女主说出自己的名字，主角看见了女主真实样貌后觉得熟悉，才后知后觉的发现是自己穿越前看过的电影中的女主角的翻版。
5. 描写副食店的排队场景。
6. 要强调年代里粮票的珍贵。
7. 突出大院里那种压抑的邻里监视感。
8. 增加对食物香气和口感的细节描写，要写出那种在物资匮乏年代，肉香飘满全院，馋得棒梗流哈喇子、小当哭闹的画面感。
9. 压抑后爆发的要求：前1/3篇幅描写禽兽的嚣张和道德绑架，后2/3篇幅描写主角的无情反击，回扣要狠，不留余地。
10.注入“京味儿”方言：台词中多加入“爷们儿”、“没跑儿”、“不吝”、“拿大顶”等地道老北京话，增加时代代入感。
11.避免多次使用“AI生成感”强烈的短语（例如“嘴角勾起一抹XX的弧度”、“空气仿佛凝固了”，死寂，寂静，疯狂，涟漪，好像，仿佛，凝固，重锤，毒蛇，取而代之，不易察觉，死一般，沉重，凝滞，铁锤，天雷，淬了毒，淬了冰，丝滑，然而，随之而来，不可避免，浓得化不开, 丝丝缕缕,仿佛/如同、深吸一口气、前所未有，繁复的, 狰狞又华贵, 沉甸甸的, 一片混沌, 枯槁的, 空荡荡的, 不甘和威严, 深沉如渊, 嗡的一声, 五味杂陈, 冰冷的机械音, 毫无征兆地, 神清气爽, 踉跄一步, 突兀, 大脑宕机, 连滚带爬, 面面相觑, 精光一闪而过，浓重的, 繁复的, 突兀地, 毫无感情的, 戛然而止，轰、炸开、就像是、嘴角勾起、取而代之的是、顿时、紧锁、立刻、连忙、显然、似乎、虽然、大致、确实、几乎、可能、注定、接下来、渐渐、更是、一定、或许、十分、沉重、看不出、淡淡、郑重、此刻、恐怕、清淡、不知道、似乎、心中一凛、眼中闪过一丝惊讶、行云流水、心下了然、话锋一转、眼神深邃、显著、至关重要、微微挑眉、波涛汹涌、绝对、不可估量、仿佛、随时、无法想象、无法用言语形容、此刻、显然、脸上带着笑意、平静地、显得有些兴奋、心中了然、激动地、眼神热切、目光里毫不遮掩、淡淡地、不卑不亢、仿佛，如同、可能、显得异常清晰、暂时、他/她知道、像是、不断、像、瞬间、这一刻、再次、嘴角勾起一抹、一时之间、这一次、看似、微微挑眉、沉吟、隐隐有了猜测、心中了然、淡淡地应了一句、不卑不亢、目光扫过、心中一片平静、显得更加……、知道、一丝、坚定、xx的眼神、深吸一口气、缓缓地说、锐利的眼睛、他的嘴角微微上扬、他的表情变暗、他的心一跳、他的脸变了、不容置疑、嘴角、脸色、不易察觉、的目光、心中、觉得、意识到、感觉到、认为、一抹、一股、似乎、些许、有点、略微、带着...、猛地、口吻、纯粹、冰冷、电弧、闪烁、裹挟、清冷、沸腾、郑重、扭曲、撕裂、漆黑、窒息、剧痛、心中一动、不动声色、小心翼翼、沉吟片刻、心里隐隐有了猜测、我知道、果然、脸上堆满了笑、像淬了毒的匕首、刺入……的心脏、嘴角勾起一个……的弧度、……看得目瞪口呆、嘴巴张得能塞下一个鸡蛋、却比……还要冰冷、像在看一个……的人、透露出的寒意、让空气的温度都下降了几度、声音不大，却……、声音平静、却重重砸在……的心头、时间仿佛被按下了暂停、带着一丝、声音坚定、眼神坚定、眼神锐利、不可置信、不可置疑、仿佛、如同、指节泛白、空气凝滞如铁、死寂、沉寂、以一种、他知道、这不是……而是、只是、冷寂、眼中流露出……的表情、我都要烦死了、声音轻细，却重重砸在……的心头、时间仿佛被按下了暂停、我知道，我赢了、如同、好像、似乎、充满、带着一丝、以及、声音坚定、眼神坚定、眼神锐利、不可置信、不可置疑、嘴角勾起一抹弧度、仿佛、如同、指节泛白、一丝、在……炸开、带着不容置疑的……、声音不大、炸雷、炸开 精准地 僵住了 凝固 甜腻 扯出 力道大得惊人 闷响 诅咒 冰凉 宣战 近乎偏执 巨大、彻底、像一台精密的仪器、无法形容、）。
12.在与女主及暧昧对象或年轻漂亮的女性互动时增加雪白内容描写及叙事。
13.对四合院内众禽兽打脸或反击侵犯自己权益时不使用系统的情况下多用“以其人之道还治其人之身”，“以势压人”的办法。
14.可以增加“屎尿屁”的禽兽恶心男女主方式，男女主整治打脸方式也可使用“屎尿屁”的方式。
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
    
    【前情提要（严禁重复此处内容）】：
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
        update_state_via_ai(client, new_chapter_content, old_state_data)

    except Exception as e:
        print(f"❌ 运行过程中出错：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    write_novel()
