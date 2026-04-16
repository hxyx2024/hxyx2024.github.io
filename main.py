from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import re
import os

# 你的配置（已填好）
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60

# 输出文件
DATA_FILE = "lottery_data_api.html"
COUNT_FILE = "count.txt"

# 读取采集次数
def get_count():
    try:
        if os.path.exists(COUNT_FILE):
            with open(COUNT_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
    except:
        return 0
    return 0

# 保存采集次数
def save_count(n):
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        f.write(str(n))

# 获取最后一期的期号
def get_last_period_num():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            lines = [x.strip() for x in f if x.strip()]
        if not lines:
            return None
        match = re.search(r"第:(\d+)期", lines[-1])
        return match.group(1) if match else None
    except:
        return None

async def main():
    count = get_count()
    if count >= MAX_TOTAL:
        print("✅ 已采满60期，自动停止")
        return

    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.connect()
        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)

        if not msg or not msg[0].text:
            print("⚠️ 未获取到消息")
            return

        text = msg[0].text
        matches = re.findall(r"第:\d+期.*?$", text, re.MULTILINE)
        if not matches:
            print("⚠️ 未匹配到数据")
            return

    except Exception as e:
        print(f"⚠️ 运行异常: {e}")
        return

    # 第一次运行清空数据
    if count == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("")

    last_num = get_last_period_num()
    target_line = None

    if last_num is None:
        target_line = matches[-1].strip()
    else:
        want = str(int(last_num) - 1)
        for line in reversed(matches):
            if want in line:
                target_line = line.strip()
                break

    if not target_line:
        print("⚠️ 未找到目标期数")
        return

    # 新数据加到最上面
    existing = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            existing = [x.strip() for x in f if x.strip()]

    final_lines = [target_line] + existing

    # 写入文件
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    save_count(count + 1)
    print(f"✅ 采集成功：{count+1}/60")

if __name__ == "__main__":
    asyncio.run(main())
