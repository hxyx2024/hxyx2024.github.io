import os
import json
import asyncio
import re
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
DATA_FILE = "lottery_data.json"
OFFSET_FILE = ".last_offset.json"
CLEAN_FLAG_FILE = ".last_clean_date"

TARGET_PERIODS = 100
BATCH_SIZE = 20
BEIJING_TZ = timezone(timedelta(hours=8))

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

def should_reset_offset():
    """每天第一次运行返回 True，重置 offset_id"""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w', encoding='utf-8') as f:
        f.write(today)
    return True

def load_offset():
    if should_reset_offset():
        print("今日首次运行，从最新消息开始拉取")
        return 0
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f).get('offset_id', 0)
            except:
                return 0
    return 0

def save_offset(offset_id):
    with open(OFFSET_FILE, 'w', encoding='utf-8') as f:
        json.dump({'offset_id': offset_id}, f)

async def fetch_batch(client, batch_size):
    items = []
    offset_id = load_offset()
    last_msg_id = 0
    loops = 0
    max_loops = 20

    existing = load_json()
    existing_periods = {item['period'] for item in existing}

    while len(items) < batch_size and loops < max_loops:
        loops += 1
        print(f"翻页 {loops}，offset_id: {offset_id}")
        msg_count = 0

        async for msg in client.iter_messages(CHANNEL, limit=100, offset_id=offset_id):
            msg_count += 1
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
            existing_periods.add(period)
            print(f"采集到: {period}")
            last_msg_id = msg.id

            if len(items) >= batch_size:
                break

        if msg_count == 0:
            print("没有更多消息，已翻到底")
            break

        if last_msg_id > 0:
            offset_id = last_msg_id
        else:
            break

    if len(items) > 0:
        save_offset(offset_id)

    return items

async def main():
    print("=== 拉取历史数据到 JSON ===")

    existing = load_json()
    print(f"JSON 中已有 {len(existing)} 期")

    # 不再判断是否达到 100 期，每次都拉取
    client = await TelegramClient("session", API_ID, API_HASH).start()
    try:
        new_items = await fetch_batch(client, BATCH_SIZE)
        if not new_items:
            print("没有新数据可拉")
            return

        all_data = existing + new_items
        all_data.sort(key=lambda x: x['period'])

        # 截断到 100 期，保留最新的 100 期
        if len(all_data) > TARGET_PERIODS:
            all_data = all_data[-TARGET_PERIODS:]

        save_json(all_data)
        print(f"✅ JSON 已更新，共 {len(all_data)} 期，本次新增 {len(new_items)} 期")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
