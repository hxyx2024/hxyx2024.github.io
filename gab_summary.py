import os
import asyncio
import re
import random
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
FETCH_LIMIT = 500          # 拉取足够多的消息，确保覆盖60期以上
OUTPUT_FILE = "gab_summary.html"

# 匹配期号：支持 "新澳门六合彩第:2026050期" 或 "新澳门第:2026050期" 等
PERIOD_RE = re.compile(r"新澳门(?:六合彩)?第[:\s]*(\d{7})期")

def extract_period(text):
    m = PERIOD_RE.search(text)
    return int(m.group(1)) if m else 0

def extract_numbers_from_line(line):
    """从一行文本中提取所有数字（1-49），返回列表"""
    nums = re.findall(r'\d+', line)
    return [int(n) for n in nums if 1 <= int(n) <= 49]

async def fetch_lotteries(client, limit):
    """拉取消息，返回列表 [(period, [7个数字]), ...] 按期号降序，去重"""
    period_map = {}
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if not txt:
            continue
        
        # 提取期号
        period = extract_period(txt)
        if period == 0:
            continue
        
        # 如果期号已存在，跳过（去重）
        if period in period_map:
            continue
        
        # 在消息中寻找包含至少7个数字的行（开奖数字）
        lines = txt.split('\n')
        numbers = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            nums = extract_numbers_from_line(line)
            if len(nums) >= 7:
                # 只取前7个数字
                numbers = nums[:7]
                break
        if numbers is None or len(numbers) != 7:
            print(f"⚠️ 期号 {period} 未能提取到7个数字，跳过")
            continue
        
        period_map[period] = numbers
        print(f"✅ 采集到期号 {period}，数字 {numbers}")
    
    # 按期号降序排序
    items = sorted(period_map.items(), key=lambda x: x[0], reverse=True)
    print(f"共采集到 {len(items)} 期，期号范围 {items[-1][0]} ~ {items[0][0]}")
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
        ga_numbers.extend(nums[:6])   # 前6个
        ga_numbers.extend(nums)       # 全部7个
    for period, nums in latest_60:
        ga_numbers.append(nums[-1])   # 最后1个
    
    gb_numbers = []
    for period, nums in latest_30:
        gb_numbers.extend(nums)
    
    # 随机排序（如果不需要随机，可注释下面两行）
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
