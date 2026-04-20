import os
import asyncio
import re
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
FETCH_LIMIT = 200
OUTPUT_FILE = "antdata.html"

# 严格匹配“新澳门六合彩第”后跟7位数字
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

async def fetch_all_te_numbers(client, limit):
    """采集所有符合格式的消息，返回列表 [(period, te_number), ...]"""
    items = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if not txt:
            continue
        period = extract_period(txt)
        if period == 0:
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
            continue
        te = numbers[-1]
        items.append((period, te))
        print(f"采集到: 期号 {period}, 特码 {te}")
    print(f"共采集到 {len(items)} 条有效消息")
    return items

async def main():
    client = await TelegramClient("session_ga", API_ID, API_HASH).start()
    try:
        items = await fetch_all_te_numbers(client, FETCH_LIMIT)
        if not items:
            print("未采集到任何开奖数据")
            return
        # 按期号降序排序（期号大的在前）
        items.sort(key=lambda x: x[0], reverse=True)
        latest_60 = items[:60]
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for period, te in latest_60:
                f.write(f"{te}\n")
        print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(latest_60)} 个特码（按期号降序）")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
