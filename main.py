from telethon import TelegramClient
import asyncio
import re
import random
import os
from datetime import datetime, timezone, timedelta

# ================== 配置 ==================
API_ID = 3608828
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"

# 手动触发固定采集数量
MANUAL_FETCH_LIMIT = 30

# ================== 辅助函数 ==================
def get_fetch_limit(is_manual):
    if is_manual:
        return MANUAL_FETCH_LIMIT
    now = datetime.now(BEIJING_TZ)
    hour = now.hour
    if 18 <= hour < 20:
        return random.randint(1, 4)
    elif 20 <= hour < 21:
        return random.randint(1, 5)
    else:
        return 0

def need_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, "r") as f:
            last_clean = f.read().strip()
        if last_clean == today:
            return False
    with open(CLEAN_FLAG_FILE, "w") as f:
        f.write(today)
    return True

period_pattern = re.compile(r"第[:\s]*(\d+)期")
def get_period(text):
    m = period_pattern.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text):
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
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
    # 直接通过 GitHub 环境变量判断是否为手动触发
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    is_manual = (event_name == "workflow_dispatch")
    print(f"触发事件: {event_name}, 手动模式: {is_manual}")

    if need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("🗑️ 今日首次运行，已清空旧内容")

    fetch_limit = get_fetch_limit(is_manual)
    if fetch_limit == 0:
        print("⏰ 不在采集时段（18:00-21:00），且非手动触发，退出")
        return
    print(f"本次采集 {fetch_limit} 条")

    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    messages = await client.get_messages(CHANNEL, limit=fetch_limit)
    await client.disconnect()

    new_data = []
    for msg in messages:
        if msg.text and "新澳门六合彩第" in msg.text:
            full = msg.text.strip()
            if is_complete_lottery(full):
                new_data.append(full)
            else:
                print(f"⚠️ 跳过不完整消息: {full[:60]}...")

    new_data = sorted(new_data, key=get_period, reverse=True)

    # 读取旧内容，过滤不完整记录
    old_lines = []
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            candidates = content.split('\n\n')
            for cand in candidates:
                cand = cand.strip()
                if cand and is_complete_lottery(cand):
                    old_lines.append(cand)
                else:
                    print(f"⚠️ 丢弃旧文件中的不完整记录: {cand[:50]}...")

    existing_periods = {get_period(line) for line in old_lines}
    all_lines = old_lines.copy()
    for line in new_data:
        p = get_period(line)
        if p not in existing_periods:
            existing_periods.add(p)
            all_lines.append(line)

    all_lines = sorted(all_lines, key=get_period)  # 升序（小→大）
    if len(all_lines) > MAX_KEEP:
        all_lines = all_lines[-MAX_KEEP:]

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_lines) + "\n")

    print(f"✅ 完成 | 共 {len(all_lines)} 期，本次新增 {len(new_data)} 期")

if __name__ == "__main__":
    asyncio.run(main())
