import os
import asyncio
import re
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"
LIMIT = 4

period_pattern = re.compile(r"第[:\s]*(\d{7})期")

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

def get_local_data():
    if not os.path.exists(OUT_FILE):
        return []
    with open(OUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    blocks = content.split('\n\n')
    valid = []
    seen = set()
    for b in blocks:
        b = b.strip()
        if b.startswith('<!--'):
            continue
        if not b or not is_complete_lottery(b):
            continue
        p = get_period(b)
        if p and p not in seen:
            seen.add(p)
            valid.append(b)
    valid.sort(key=get_period)
    return valid

def need_auto_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w') as f:
        f.write(today)
    return True

async def fetch_recent_messages(client):
    """强制获取最新消息，不使用缓存"""
    valid = []
    # 显式 reverse=False 从最新开始，min_id=0 强制刷新
    async for msg in client.iter_messages(
        CHANNEL,
        limit=LIMIT,
        reverse=False,
        min_id=0,
        wait_time=0
    ):
        if msg.text and "第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                valid.append(txt)
                if len(valid) >= LIMIT:
                    break
    # 反转顺序，从旧到新
    valid.reverse()
    return valid

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"{'手动' if is_manual else '自动'}触发")

    if is_manual:
        open(OUT_FILE, 'w').close()
        print("已清空文件")
    elif need_auto_clean_today():
        open(OUT_FILE, 'w').close()
        print("今日首次运行，已清空文件")

    client = await TelegramClient("session", API_ID, API_HASH).start()
    await client.get_me()  # 强制刷新会话

    try:
        local_data = [] if is_manual else get_local_data()
        local_periods = {get_period(b) for b in local_data}

        all_valid = await fetch_recent_messages(client)
        print(f"获取到 {len(all_valid)} 条有效开奖，期号: {[get_period(t) for t in all_valid]}")

        if not all_valid:
            return

        new_periods = [txt for txt in all_valid if get_period(txt) not in local_periods]
        if not new_periods:
            print("无新期号")
            return

        all_blocks = local_data + new_periods
        unique = {get_period(b): b for b in all_blocks}
        sorted_blocks = [unique[p] for p in sorted(unique.keys())]
        if len(sorted_blocks) > MAX_KEEP:
            sorted_blocks = sorted_blocks[-MAX_KEEP:]

        content = "\n\n".join(sorted_blocks) + "\n"
        if is_manual:
            ts = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
            content += f"<!-- 手动更新于 {ts} -->\n"

        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"写入完成，共 {len(sorted_blocks)} 期")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
