from telethon import TelegramClient
import asyncio
import re
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHANNEL = "@douapi"

DATA_FILE = "lottery_data.txt"

def read_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def get_last_period():
    lines = read_data()
    if not lines:
        return None
    match = re.search(r"第:(\d+)期", lines[-1])
    return int(match.group(1)) if match else None

async def run():
    lines = read_data()
    last = get_last_period()

    client = TelegramClient("github_session", API_ID, API_HASH)
    await client.start()

    chat = await client.get_entity(CHANNEL)
    msg = await client.get_messages(chat, limit=1)
    if not msg:
        return

    text = msg[0].text
    matches = re.findall(r"第:(\d+)期.*?\n([\d\s]+)\n(.*?)\n(.*?)$", text, re.DOTALL)
    if not matches:
        return

    period, nums, sx, color = matches[-1]
    line = f"新澳门六合彩第:{period}期开奖结果: {nums} {sx} {color}"

    if not last or int(period) > last:
        lines.append(line)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(lines))

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run())
