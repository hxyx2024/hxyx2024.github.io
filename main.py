from telethon import TelegramClient
import asyncio
import re
import os

# 改成你自己的 API
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"

DATA_FILE = "lottery_data_api.html"

# 读取已有数据
def get_lines():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except:
        return []

# 获取最后一期
def get_last_period():
    lines = get_lines()
    if not lines:
        return None
    m = re.search(r"第:(\d+)期", lines[-1])
    return int(m.group(1)) if m else None

async def main():
    lines = get_lines()
    last = get_last_period()

    # 登录（服务器上第一次会提示输入手机号）
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()

    # 获取最新一条消息
    chat = await client.get_entity(CHANNEL)
    msg = await client.get_messages(chat, limit=1)
    if not msg or not msg[0].text:
        print("未获取到内容")
        return

    text = msg[0].text

    # 匹配你这种格式
    pattern = re.compile(
        r"第:(\d+)期开奖结果:\s*\n([\d\s]+)\n(.+)\n(.+)",
        re.DOTALL
    )
    matches = list(pattern.finditer(text))
    if not matches:
        print("未匹配到开奖信息")
        return

    # 找最新一期
    target = matches[-1]
    period = target.group(1)
    nums = target.group(2).strip()
    sx = target.group(3).strip()
    color = target.group(4).strip()

    line = f"新澳门六合彩第:{period}期开奖结果: {nums} {sx} {color}"

    # 期数大的放最下面
    new_lines = lines + [line]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_lines))

    print(f"✅ 采集成功：{period}期")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
