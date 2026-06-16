import os
import json
import asyncio
import re
from telethon import TelegramClient

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
DATA_FILE = "lottery_data.json"

TARGET_PERIODS = 100   # 目标总期数
BATCH_SIZE = 20        # 每次拉取期数

# ========== 工具函数 ==========
period_pattern = re.compile(r"新澳门六合彩第[:\s]*(\d{7})期")

def get_period(text):
    m = period_pattern.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text):
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 4:
        return False
    if not re.search(r'\d+\s+\d+', lines[1]):
        return False
    if not re.search(r'[鼠牛虎兔龍蛇馬羊猴雞狗豬]', lines[2]):
        return False
    if not re.search(r'[🟢🔴🔵]', lines[3]):
        return False
    return True

def load_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_json(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def fetch_batch(client, batch_size):
    """翻页拉取 batch_size 期，返回列表"""
    items = []
    offset_id = 0
    
    # 获取已有期号，用于去重
    existing = load_json()
    existing_periods = {item['period'] for item in existing}
    
    while len(items) < batch_size:
        async for msg in client.iter_messages(CHANNEL, limit=100, offset_id=offset_id):
            if not msg.text:
                continue
            txt = msg.text.strip()
            if not txt:
                continue
            if "新澳门六合彩第" not in txt:
                continue
            if not is_complete_lottery(txt):
                continue
            period = get_period(txt)
            if period == 0:
                continue
            if period in existing_periods:
                continue
            items.append({"period": period, "text": txt})
            print(f"采集到: {period}")
            if len(items) >= batch_size:
                break
            offset_id = msg.id
        if len(items) == 0:
            break
    return items

async def main():
    print("=== 拉取历史数据到 JSON ===")
    
    # 检查现有数据
    existing = load_json()
    print(f"JSON 中已有 {len(existing)} 期")
    
    if len(existing) >= TARGET_PERIODS:
        print(f"已达到目标 {TARGET_PERIODS} 期，无需拉取")
        return
    
    client = await TelegramClient("session", API_ID, API_HASH).start()
    try:
        # 拉取一批
        new_items = await fetch_batch(client, BATCH_SIZE)
        if not new_items:
            print("没有新数据可拉")
            return
        
        # 合并去重
        existing_periods = {item['period'] for item in existing}
        all_data = existing + [item for item in new_items if item['period'] not in existing_periods]
        
        # 按 period 升序排序（从早到晚）
        all_data.sort(key=lambda x: x['period'])
        
        # 截断到 TARGET_PERIODS（保留最早的 100 期）
        if len(all_data) > TARGET_PERIODS:
            all_data = all_data[:TARGET_PERIODS]
        
        save_json(all_data)
        print(f"✅ JSON 已更新，共 {len(all_data)} 期")
        print(f"本次新增 {len(new_items)} 期")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
