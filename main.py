from telethon import TelegramClient
import asyncio
import re
import os
from datetime import datetime

# 你的配置
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
DATA_FILE = "lottery_data_api.html"

# 获取当前已采集行数
def get_lines():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except:
        return []

# 获取最后一期（最大的数字）
def get_last_num():
    lines = get_lines()
    if not lines:
        return None
    match = re.search(r"第:(\d+)期", lines[-1])
    return match.group(1) if match else None

async def main():
    now = datetime.now()
    h = now.hour
    lines = get_lines()
    total = len(lines)

    # 满60期直接停止
    if total >= MAX_TOTAL:
        print("✅ 已采满60期，自动停止")
        return

    # 时间控制
    is_18_20 = 18 <= h < 20
    is_20_21 = 20 <= h < 21

    if not is_18_20 and not is_20_21:
        print("当前不在采集时间段")
        return

    # 18~20点 最多采30期
    if is_18_20 and total >= 30:
        print("✅ 18-20点已采满30期，等待20点后继续")
        return

    # 采集频道数据
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.connect()
        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)
        if not msg or not msg[0].text:
            return
        text = msg[0].text
        matches = re.findall(r"第:\d+期.*?$", text, re.MULTILINE)
        if not matches:
            return
    except:
        return

    # 第一次采集清空
    if total == 0:
        lines = []
        print("🗑️ 首次采集，已清空旧数据")

    last_num = get_last_num()
    target = None

    if last_num is None:
        target = matches[-1].strip()
    else:
        want = str(int(last_num) - 1)
        for line in reversed(matches):
            if want in line:
                target = line.strip()
                break

    if not target:
        print("⚠️ 暂无新期数")
        return

    # 新内容 + 旧内容（新的在最上面）
    new_lines = [target] + lines

    # 保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_lines))

    print(f"✅ 采集成功 | 累计：{len(new_lines)}/60")

if __name__ == "__main__":
    asyncio.run(main())
