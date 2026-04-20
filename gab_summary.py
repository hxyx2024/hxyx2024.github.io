import os
import asyncio
import re
import random
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
FETCH_LIMIT = 500

OUTPUT_HTML = "gab_summary.html"
OUTPUT_RULES = "default_rules.txt"

# ---------- 开奖消息处理 ----------
PERIOD_RE = re.compile(r"新澳门六合彩第[:\s]*(\d{7})期")

def extract_period(text):
    m = PERIOD_RE.search(text)
    return int(m.group(1)) if m else 0

def is_valid_number_line(line):
    """检查一行是否为恰好7个数字（1-49），且只包含数字和空格"""
    line = line.strip()
    if not line:
        return False
    if re.search(r'[^0-9\s]', line):
        return False
    nums = re.findall(r'\d+', line)
    if len(nums) != 7:
        return False
    for n in nums:
        num = int(n)
        if num < 1 or num > 49:
            return False
    return True

async def fetch_lotteries(client, limit):
    """采集开奖消息，返回列表 [(period, [7个数字]), ...] 按期号降序，去重"""
    period_map = {}
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if not txt:
            continue
        period = extract_period(txt)
        if period == 0:
            continue
        if period in period_map:
            continue
        lines = txt.split('\n')
        numbers = None
        for line in lines:
            if is_valid_number_line(line):
                nums = [int(n) for n in re.findall(r'\d+', line)]
                if len(nums) == 7:
                    numbers = nums
                    break
        if numbers is None:
            print(f"⚠️ 期号 {period} 未找到恰好7个数字的行，跳过")
            continue
        period_map[period] = numbers
        print(f"✅ 采集到期号 {period}，数字 {numbers}")
    items = sorted(period_map.items(), key=lambda x: x[0], reverse=True)
    print(f"共采集到 {len(items)} 期，期号范围 {items[-1][0]} ~ {items[0][0]}")
    return [(period, nums) for period, nums in items]

def generate_ga_gb_html(lotteries):
    if not lotteries:
        return "暂无数据"
    latest_60 = lotteries[:60]
    latest_10 = lotteries[:10]
    latest_30 = lotteries[:30]
    top_period = latest_60[0][0] + 1 if latest_60 else 0

    ga_numbers = []
    for period, nums in latest_10:
        ga_numbers.extend(nums[:6])
        ga_numbers.extend(nums)
    for period, nums in latest_60:
        ga_numbers.append(nums[-1])

    gb_numbers = []
    for period, nums in latest_30:
        gb_numbers.extend(nums)

    random.shuffle(ga_numbers)
    random.shuffle(gb_numbers)

    ga_line = " ".join(str(n) for n in ga_numbers)
    gb_line = " ".join(str(n) for n in gb_numbers)

    lines = [
        f"新澳彩第: {top_period}期",
        "GA",
        ga_line,
        "",
        "...................",
        "",
        "GB",
        gb_line
    ]
    return "\n".join(lines)

# ---------- 规则格式消息处理 ----------
def is_rules_format(text):
    """检查消息是否全部由类似 '数字 数字' 的行组成（可含空行）"""
    lines = text.strip().split('\n')
    if not lines:
        return False
    for line in lines:
        line = line.strip()
        if line == "":
            continue
        if not re.match(r'^\d{1,2}\s+\d{1,2}$', line):
            return False
    return True

async def fetch_rules(client, limit):
    """采集最新的规则格式消息（只取最新一条）"""
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if is_rules_format(txt):
            return txt
    return None

# ---------- 主函数 ----------
async def main():
    client = await TelegramClient("session", API_ID, API_HASH).start()
    try:
        # 1. 采集开奖消息并生成 gab_summary.html
        lotteries = await fetch_lotteries(client, FETCH_LIMIT)
        if lotteries:
            html_content = generate_ga_gb_html(lotteries)
            with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ 已生成 {OUTPUT_HTML}")
        else:
            print("未采集到任何开奖消息，不生成 gab_summary.html")

        # 2. 采集规则消息并生成 default_rules.txt
        rules_text = await fetch_rules(client, FETCH_LIMIT)
        if rules_text:
            with open(OUTPUT_RULES, 'w', encoding='utf-8') as f:
                f.write(rules_text + "\n")
            print(f"✅ 已生成 {OUTPUT_RULES}")
        else:
            print("未采集到规则格式消息，不生成 default_rules.txt")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
