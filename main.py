from telethon import TelegramClient
import asyncio
import re
import random
import os
from datetime import datetime, timezone, timedelta

# ========== 从环境变量读取敏感信息 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))

# 手动触发固定采集条数
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
    # 判断是否手动触发
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动模式: {is_manual}")
    print(f"北京时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")

    limit = get_fetch_limit(is_manual)
    if limit == 0:
        print("不在采集时段且非手动，退出")
        return
    print(f"本次采集 {limit} 条")

    # 连接 Telegram
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    msgs = await client.get_messages(CHANNEL, limit=limit)
    await client.disconnect()

    # 提取完整的开奖消息
    new_data = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                new_data.append(txt)

    new_data.sort(key=get_period, reverse=True)

    # 读取已有数据（使用 \n---\n 作为分隔符）
    old = []
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            # 按分隔符分割
            for block in content.split("\n---\n"):
                block = block.strip()
                if block and is_complete_lottery(block):
                    old.append(block)

    # 去重合并
    exist_periods = {get_period(x) for x in old}
    all_data = old[:]
    for line in new_data:
        p = get_period(line)
        if p not in exist_periods:
            exist_periods.add(p)
            all_data.append(line)

    all_data.sort(key=get_period)   # 升序（早期在前）
    if len(all_data) > MAX_KEEP:
        all_data = all_data[-MAX_KEEP:]

    # 写入文件，使用 \n---\n 分隔
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n---\n".join(all_data))
        if all_data:
            f.write("\n")   # 末尾换行

    print(f"完成，共 {len(all_data)} 期，新增 {len(new_data)} 期")

if __name__ == "__main__":
    asyncio.run(main())
