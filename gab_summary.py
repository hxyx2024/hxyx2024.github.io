import os
import asyncio
import re
import random
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
FETCH_LIMIT = 200
OUTPUT_FILE = "gab_summary.html"

PERIOD_RE = re.compile(r"新澳门(?:六合彩)?第[:\s]*(\d{7})期")

def extract_period(text):
    m = PERIOD_RE.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text):
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 4:
        return False
    nums = re.findall(r'\d+', lines[1])
    if len(nums) != 7:
        return False
    zodiacs = re.findall(r'[鼠牛虎兔龍蛇馬羊猴雞狗豬]', lines[2])
    if len(zodiacs) != 7:
        return False
    colors = re.findall(r'[🟢🔴🔵]', lines[3])
    if len(colors) != 7:
        return False
    return True

def parse_numbers(text):
    lines = text.split('\n')
    if len(lines) < 2:
        return []
    nums = re.findall(r'\d+', lines[1])
    return [int(n) for n in nums[:7]]

async def fetch_lotteries(client, limit):
    items = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if not is_complete_lottery(txt):
            continue
        period = extract_period(txt)
        if period == 0:
            continue
        numbers = parse_numbers(txt)
        if len(numbers) != 7:
            continue
        items.append((period, numbers))
    items.sort(key=lambda x: x[0], reverse=True)
    return items

def generate_plain_text(lotteries):
    if not lotteries:
        return "暂无数据"
    
    latest_60 = lotteries[:60]
    latest_10 = lotteries[:10]
    latest_30 = lotteries[:30]
    
    # 顶部期号 = 最新60期中的最新一期实际期号+1
    top_period = latest_60[0][0] + 1 if latest_60 else 0
    
    # 收集GA数字
    ga_numbers = []
    # 最新10期的前6个数字和全部7个数字
    for period, nums in latest_10:
        ga_numbers.extend(nums[:6])   # 前6个
        ga_numbers.extend(nums)       # 全部7个
    # 最新60期的最后1个数字
    for period, nums in latest_60:
        ga_numbers.append(nums[-1])
    
    # 收集GB数字：最新30期的全部7个数字
    gb_numbers = []
    for period, nums in latest_30:
        gb_numbers.extend(nums)
    
    # 随机排序
    random.shuffle(ga_numbers)
    random.shuffle(gb_numbers)
    
    # 格式化为空格分隔的字符串
    ga_line = " ".join(str(n) for n in ga_numbers)
    gb_line = " ".join(str(n) for n in gb_numbers)
    
    lines = [
        f"新澳门第:{top_period}期",
        "G · A",
        ga_line,
        "...........",
        "G · B",
        gb_line
    ]
    return "\n".join(lines)

async def main():
    client = await TelegramClient("session", API_ID, API_HASH).start()
    try:
        lotteries = await fetch_lotteries(client, FETCH_LIMIT)
        if not lotteries:
            print("未拉取到任何有效开奖数据")
            return
        plain_text = generate_plain_text(lotteries)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(plain_text)
        print(f"✅ 已生成 {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
