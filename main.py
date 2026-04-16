from telethon import TelegramClient
import asyncio
import re
import os

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"

# 国内机器用 V2Ray 代理（你是10808）
PROXY = (socks.SOCKS5, "127.0.0.1", 10808)

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

async def main():
    lines = get_lines()
    last = get_last_period()

    client = TelegramClient("session", API_ID, API_HASH, proxy=PROXY)
    await client.start()  # 这里会让你输入手机号+验证码

    chat = await client.get_entity(CHANNEL)
    msg = await client.get_messages(chat, limit=1)
    if not msg:
        print("无消息")
        return

    text = msg[0].text
    pattern = re.compile(r"第:(\d+)期开奖结果:(.*?)\n([\d\s]+)\n(.*?)\n(.*)", re.DOTALL)
    matches = list(pattern.finditer(text))

    target = None
    if last is None:
        target = matches[-1]
    else:
        for m in reversed(matches):
            if int(m.group(1)) == last - 1:
                target = m
                break

    if not target:
        print("暂无新期数")
        return

    period = target.group(1)
    nums = target.group(3).strip()
    sx = target.group(4).strip()
    color = target.group(5).strip()

    line = f"新澳门六合彩第:{period}期开奖结果: {nums} {sx} {color}"
    new_lines = lines + [line]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_lines))

    print(f"✅ 采集成功：{period}期")

if __name__ == "__main__":
    asyncio.run(main())
