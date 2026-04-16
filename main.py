from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import re
import os

# ========== 你的配置 ==========
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
# 登录字符串（第一次运行后会自动保存）
STRING_SESSION = ""
# ==============================

DATA_FILE = "lottery_data_api.html"
COUNT_FILE = "count.txt"

def get_count():
    if not os.path.exists(COUNT_FILE):
        return 0
    try:
        return int(open(COUNT_FILE, encoding="utf-8").read().strip())
    except:
        return 0

def save_count(n):
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        f.write(str(n))

def get_last_period_num():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return None
        match = re.search(r"第:(\d+)期", lines[-1])
        return match.group(1) if match else None
    except:
        return None

async def main():
    count = get_count()
    if count >= MAX_TOTAL:
        print("已满60期，停止运行")
        return

    try:
        if STRING_SESSION:
            client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
        else:
            client = TelegramClient(StringSession(), API_ID, API_HASH)

        await client.connect()
        if not await client.is_user_authorized():
            print("❌ 请在本地先登录一次获取 StringSession")
            return

        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)
        if not msg or not msg[0].message:
            return

        text = msg[0].message.strip()
        pattern = re.compile(r"(第:\d+期.*?$)", re.DOTALL | re.MULTILINE)
        matches = pattern.findall(text)
        if not matches:
            return

    except Exception as e:
        print(f"⚠️ 登录或采集异常: {e}")
        return

    # 第一次清空
    if count == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("")

    last_num = get_last_period_num()
    target_line = None

    if last_num is None:
        target_line = matches[-1].strip()
    else:
        want_num = str(int(last_num) - 1)
        for line in reversed(matches):
            if want_num in line:
                target_line = line.strip()
                break

    if not target_line:
        return

    existing = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            existing = [line.strip() for line in f if line.strip()]

    final_lines = [target_line] + existing

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    save_count(count + 1)
    print(f"✅ 已采集 {count+1}/{MAX_TOTAL} 期")

if __name__ == "__main__":
    asyncio.run(main())
