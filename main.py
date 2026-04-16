from telethon import TelegramClient
import asyncio
import re
import os
from datetime import datetime

# ========== 你的配置 ==========
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
DATA_FILE = "lottery_data_api.html"

# 获取所有已保存数据
def get_lines():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

# 获取最后一期（最大期号）
def get_last_period():
    lines = get_lines()
    if not lines:
        return None
    # 匹配 2026105 这种期号
    match = re.search(r"第:(\d+)期", lines[-1])
    return int(match.group(1)) if match else None

async def main():
    now = datetime.now()
    hour = now.hour
    lines = get_lines()
    total = len(lines)

    print(f"📊 已保存：{total}/{MAX_TOTAL} 期 | 当前时间：{now.strftime('%H:%M')}")

    if total >= MAX_TOTAL:
        print("✅ 已采满60期，停止")
        return

    # 采集时间段 18:00~21:00
    if not (18 <= hour < 21):
        print("⏰ 不在 18:00~21:00 采集时段")
        return

    # 18~20点限30期
    if 18 <= hour < 20 and total >= 30:
        print("✅ 18~20点已采够30期，等20点后")
        return

    # 登录 Telegram
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print("🔑 未登录，请先本地运行登录")
            return

        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)

        if not msg or not msg[0].text:
            print("⚠️ 未获取到消息")
            return

        text = msg[0].text

    except Exception as e:
        print(f"❌ 异常：{e}")
        return

    # ======================
    # 匹配整段开奖信息（关键修复）
    # ======================
    pattern = re.compile(
        r"新澳门六合彩第:(\d+)期开奖结果:(.*?)[\n\r]*?"
        r"([\d\s]+?)[\n\r]*?"
        r"([^\n\r]+?)[\n\r]*?"
        r"([^\n\r]+)",
        re.DOTALL
    )

    matches = list(pattern.finditer(text))
    if not matches:
        print("⚠️ 未匹配到开奖数据")
        return

    # 首次运行清空
    if total == 0:
        lines = []

    last_num = get_last_period()
    target_item = None

    if last_num is None:
        # 没数据 → 取最新一期
        target_item = matches[-1]
    else:
        want = last_num - 1
        for m in reversed(matches):
            period = int(m.group(1))
            if period == want:
                target_item = m
                break

    if not target_item:
        print("⚠️ 暂无新期数可采")
        return

    # 组装完整一行
    period = target_item.group(1)
    nums = target_item.group(3).strip()
    shengxiao = target_item.group(4).strip()
    colors = target_item.group(5).strip()

    line = f"新澳门六合彩第:{period}期开奖结果: {nums} {shengxiao} {colors}"

    # ======================
    # 排序：期数大在最下面
    # 从上到下：96 →97 →98 →99
    # ======================
    new_lines = lines + [line]

    # 保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_lines))

    print(f"✅ 采集成功：第{period}期")
    print(f"📶 累计已保存：{len(new_lines)}/{MAX_TOTAL}")

if __name__ == "__main__":
    asyncio.run(main())
