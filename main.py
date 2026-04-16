from telethon import TelegramClient
import asyncio
import re
import os
from datetime import datetime

# ========== 你的固定配置 ==========
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
DATA_FILE = "lottery_data_api.html"

# 获取当前所有行
def get_lines():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

# 获取最后一期（最大的数字）
def get_last_period():
    lines = get_lines()
    if not lines:
        return None
    match = re.search(r"第:(\d+)期", lines[-1])
    return match.group(1) if match else None

async def main():
    now = datetime.now()
    hour = now.hour
    lines = get_lines()
    total = len(lines)

    # 满60期自动停止
    if total >= MAX_TOTAL:
        print("✅ 已采满60期，自动停止")
        return

    # 时间范围
    time_18_20 = 18 <= hour < 20
    time_20_21 = 20 <= hour < 21

    if not time_18_20 and not time_20_21:
        print("当前不在采集时间段")
        return

    # 18~20点只采30期
    if time_18_20 and total >= 30:
        print("✅ 18-20点已采够30期，等待20点后")
        return

    # 开始采集
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
        print(f"异常：{e}")
        return

    # 第一次运行清空
    if total == 0:
        lines = []
        print("🗑️ 首次采集，已清空旧数据")

    # 取上一期（期号 -1）
    last_num = get_last_period()
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
        print("⚠️ 暂无新期数可采")
        return

    # 新内容 → 最上面
    new_lines = [target] + lines

    # 保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_lines))

    print(f"✅ 采集成功 | 累计：{len(new_lines)}/60")

if __name__ == "__main__":
    asyncio.run(main())
