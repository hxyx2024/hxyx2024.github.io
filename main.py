from telethon import TelegramClient
import asyncio
import re
import os

# ========== 你的配置已全部正确填写 ==========
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "@douapi"
MAX_TOTAL = 60
# ============================================

# ✅ 已改成你要的文件名
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

    async with TelegramClient("sess", API_ID, API_HASH) as client:
        await client.start()
        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)
        if not msg or not msg[0].message:
            return

        text = msg[0].message.strip()
        pattern = re.compile(r"(第:\d+期.*?$)", re.DOTALL | re.MULTILINE)
        matches = pattern.findall(text)
        if not matches:
            return

    # 第一次采集：清空旧数据
    if count == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("")

    last_num = get_last_period_num()
    target_line = None

    if last_num is None:
        # 第一次：取最新一期
        target_line = matches[-1].strip()
    else:
        # 之后每次：期号 -1
        want_num = str(int(last_num) - 1)
        for line in reversed(matches):
            if want_num in line:
                target_line = line.strip()
                break

    if not target_line:
        return

    # 读取现有内容，新的一行加到最上面
    existing = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            existing = [line.strip() for line in f if line.strip()]

    final_lines = [target_line] + existing

    # 写入 lottery_data_api.html
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    save_count(count + 1)
    print(f"已采集 {count+1}/{MAX_TOTAL} 期")

if __name__ == "__main__":
    asyncio.run(main())
