from telethon import TelegramClient
import asyncio
import re
import random
import os
from datetime import datetime, timezone, timedelta

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"

MANUAL_FETCH_LIMIT = 30

def get_fetch_limit(is_manual):
    if is_manual:
        return MANUAL_FETCH_LIMIT
    now = datetime.now(BEIJING_TZ)
    h = now.hour
    if 18 <= h < 20:
        return random.randint(1, 4)
    elif 20 <= h < 21:
        return random.randint(1, 5)
    return 0

def need_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, "r") as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, "w") as f:
        f.write(today)
    return True

period_pattern = re.compile(r"第[:\s]*(\d+)期")
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

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动: {is_manual}")
    print(f"北京时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")

    # ========== 手动触发分支 ==========
    if is_manual:
        # 清空文件
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("手动触发：已清空文件，本次将只写入拉取到的数据（需完整格式）")
        # 更新日期标志，避免影响明天的自动清空
        need_clean_today()

        limit = MANUAL_FETCH_LIMIT
        print(f"本次采集 {limit} 条")

        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()
        msgs = await client.get_messages(CHANNEL, limit=limit)
        await client.disconnect()

        # 筛选完整开奖记录
        new_data = []
        for m in msgs:
            if m.text and "新澳门六合彩第" in m.text:
                txt = m.text.strip()
                if is_complete_lottery(txt):
                    new_data.append(txt)

        # 去重（按期数）
        unique = {}
        for item in new_data:
            p = get_period(item)
            if p not in unique:
                unique[p] = item
        all_data = list(unique.values())
        all_data.sort(key=get_period)

        # 写入文件（使用 \n\n 分隔，与自动触发保持一致）
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_data))
            if all_data:
                f.write("\n")

        print(f"手动触发完成，共写入 {len(all_data)} 期")
        return

    # ========== 自动触发原有逻辑（完全不变） ==========
    if need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，清空旧内容")

    limit = get_fetch_limit(is_manual=False)
    if limit == 0:
        print("不在采集时段，退出")
        return
    print(f"本次采集 {limit} 条")

    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    msgs = await client.get_messages(CHANNEL, limit=limit)
    await client.disconnect()

    new_data = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                new_data.append(txt)

    new_data.sort(key=get_period, reverse=True)

    old = []
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            for block in content.split('\n\n'):
                block = block.strip()
                if block and is_complete_lottery(block):
                    old.append(block)

    exist_periods = {get_period(x) for x in old}
    all_data = old[:]
    for line in new_data:
        p = get_period(line)
        if p not in exist_periods:
            exist_periods.add(p)
            all_data.append(line)

    all_data.sort(key=get_period)
    if len(all_data) > MAX_KEEP:
        all_data = all_data[-MAX_KEEP:]

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_data) + "\n")

    print(f"完成，共 {len(all_data)} 期，新增 {len(new_data)} 期")

if __name__ == "__main__":
    asyncio.run(main())
