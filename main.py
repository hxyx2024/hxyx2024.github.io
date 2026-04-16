from telethon import TelegramClient
import asyncio
import re
import os

# ========== 你的配置已填好 ==========
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
# ==================================

DATA_FILE = "lottery_data_api.html"

# 获取最后一期（最大的数字）
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
        return 0

# 获取当前条数
def get_current_count():
    if not os.path.exists(DATA_FILE):
        return 0
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            lines = [x.strip() for x in f if x.strip()]
        return len(lines)
    except:
        return 0

async def main():
    current_count = get_current_count()
    if current_count >= MAX_TOTAL:
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

    last_num = get_last_period_num()
    target_line = None

    if last_num is None:
        target_line = matches[-1].strip()
    else:
        want = str(int(last_num) + 1)
        for line in reversed(matches):
            if want in line:
                target_line = line.strip()
                break

    if not target_line:
        print("⚠️ 未找到下一期")
        return

    # 读取旧内容
    existing = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            existing = [x.strip() for x in f if x.strip()]

    # ✅ 关键：新内容 追加 在 最下面（最大数字在底部）
    final_lines = existing + [target_line]

    # 写入
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    print(f"✅ 采集成功 | 最新期数排在最底部")

if __name__ == "__main__":
    asyncio.run(main())
