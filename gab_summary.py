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
    period_map = {}
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
        if period not in period_map:
            period_map[period] = numbers
    items = sorted(period_map.items(), key=lambda x: x[0], reverse=True)
    return [(period, nums) for period, nums in items]

def generate_plain_text(lotteries):
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
