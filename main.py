from telethon import TelegramClient
import asyncio
import re
import os
import time

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"

DATA_FILE = "lottery_data_api.html"

def get_lines():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except:
        return []

def get_last_period():
    lines = get_lines()
    if not lines:
        return None
    m = re.search(r"第:(\d+)期", lines[-1])
    return int(m.group(1)) if m else None

async def job():
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()

        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)
        if not msg or not msg[0].text:
            print("未获取到消息")
            return

        text = msg[0].text
        pattern = re.compile(r"第:(\d+)期.*?\n([\d\s]+)\n(.*?)\n(.*?)$", re.DOTALL)
        matches = pattern.findall(text)
        if not matches:
            print("未匹配到数据")
            return

        period, nums, sx, color = matches[-1]
        line = f"第:{period}期: {nums} | {sx} | {color}"

        lines = get_lines()
        last = get_last_period()

        if last is None or int(period) > last:
            lines.append(line)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"✅ 已保存最新期数: {period}")
        else:
            print(f"ℹ 已是最新: {period}")

        await client.disconnect()
    except Exception as e:
        print("异常:", e)

async def main():
    while True:
        await job()
        print("等待60秒后重试...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
