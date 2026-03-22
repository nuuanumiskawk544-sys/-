import os
import sys

# ======= 纠错规则库 =======
# 违禁词：一旦出现，必须修改或警告
FORBIDDEN_WORDS = ["手机", "微信", "互联网", "扫码", "打车", "外卖"] 
# 圣母倾向词：防止主角性格走样
HOLY_MOTHER_WORDS = ["原谅他们", "算了不计较", "无私分享", "送给贾家"]

def auto_fix_content(content):
    """基础文本替换纠错"""
    fixes = {
        "原谅了贾张氏": "冷冷地看了贾张氏一眼",
        "心里一软": "心如铁石",
        "大方地把肉送给": "拎着肉当面气死",
        "对易中海点点头": "当众让易中海下不来台"
    }
    for wrong, right in fixes.items():
        if wrong in content:
            print(f"🔧 自动修正：将 [{wrong}] 修正为 [{right}]")
            content = content.replace(wrong, right)
    return content

def check_logic(content):
    """逻辑与背景核查"""
    # 检查是否有现代词汇
    for word in FORBIDDEN_WORDS:
        if word in content:
            print(f"❌ 严重错误：内容包含现代词汇 '{word}'")
            return False
    
    # 检查主角是否圣母化
    for word in HOLY_MOTHER_WORDS:
        if word in content:
            print(f"⚠️ 警告：检测到圣母倾向词 '{word}'")
            # 这里可以选择返回 False 拦截，或者仅记录
            
    return True

def run_check():
    if not os.path.exists("chapters"):
        return
    
    # 获取最新生成的文件
    files = sorted([f for f in os.listdir("chapters") if f.endswith(".md")])
    if not files:
        return
        
    latest_file = os.path.join("chapters", files[-1])
    with open(latest_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 自动执行文本替换
    fixed_content = auto_fix_content(content)
    
    # 2. 逻辑验证
    if not check_logic(fixed_content):
        print("🛑 内容质量未达标，拒绝提交！")
        sys.exit(1)

    # 3. 写回文件
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(fixed_content)
    print(f"✅ 内容质检通过：{files[-1]}")

if __name__ == "__main__":
    run_check()
