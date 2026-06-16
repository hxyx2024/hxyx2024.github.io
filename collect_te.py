import os
import asyncio
import re
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUTPUT_FILE = "antdata.html"
TARGET_PERIODS = 60   # 要拉取的新澳期数

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

async def fetch_new_macau_te_numbers(client, target_periods):
    """
    翻页拉取新澳门六合彩特码，直到凑够 target_periods 期
    返回列表 [(period, te_number), ...]
    """
    items = []
    offset_id = 0
    
    while len(items) < target_periods:
        # 每次拉 100 条消息，从最新的开始往前翻
        async for msg in client.iter_messages(CHANNEL, limit=100, offset_id=offset_id):
            if not msg.text:
                continue
            txt = msg.text.strip()
            if not txt:
                continue
            
            # 只处理新澳门六合彩
            if "新澳门六合彩第" not in txt:
                continue
            
            period = extract_period(txt)
            if period == 0:
                continue
            
            # 只处理 2026 年开头的期号（新澳门）
            if period < 2026000 or period > 2026999:
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
            
            te = numbers[-1]  # 特码 = 最后一个数字
            items.append((period, te))
            print(f"采集到: 期号 {period}, 特码 {te}")
            
            # 如果已经凑够目标期数，提前结束
            if len(items) >= target_periods:
                break
            
            # 记录当前消息ID，用于继续往前翻
            offset_id = msg.id
        
        # 如果本轮没有拉到任何消息，说明频道到底了
        if len(items) == 0:
            break
    
    print(f"共采集到 {len(items)} 期新澳门六合彩")
    return items

async def main():
    client = await TelegramClient("session_ga", API_ID, API_HASH).start()
    try:
        items = await fetch_new_macau_te_numbers(client, TARGET_PERIODS)
        if not items:
            print("未采集到任何开奖数据")
            return
        
        # 按期号降序排序（期号大的在前，最新的在前）
        items.sort(key=lambda x: x[0], reverse=True)
        
        # 只取前 TARGET_PERIODS 个
        latest_60 = items[:TARGET_PERIODS]
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for period, te in latest_60:
                f.write(f"{te}\n")
        print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(latest_60)} 个特码（新澳门最新 {TARGET_PERIODS} 期）")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
