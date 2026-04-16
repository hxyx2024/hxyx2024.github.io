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

# 自动获取最后一期的期号
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

# 自动统计已经采集了多少行
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
    # 自动判断是否采满 60 条
    current_count = get_current_count()
    if current_count >= MAX_TOTAL:
        print("✅ 已采满60期，自动停止")
        return

    try:
        # 登录客户端
        client = TelegramClient("session", API_ID, API_HASH)
        await client.connect()

        # 获取频道最新消息
        chat = await client.get_entity(CHANNEL)
        msg = await client.get_messages(chat, limit=1)

        if not msg or not msg[0].text:
            print("⚠️ 未获取到消息")
            return

        # 匹配期数数据
        text = msg[0].text
        matches = re.findall(r"第:\d+期.*?$", text, re.MULTILINE)
        if not matches:
            print("⚠️ 未匹配到数据")
            return

    except Exception as e:
        print(f"⚠️ 运行异常: {e}")
        return

    # 第一次运行：清空文件
    if current_count == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("")

    # 获取最后一期，准备取下一期（-1）
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

    # 写入 HTML 文件
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    print(f"✅ 采集成功 | 已保存：{len(final_lines)}/60")

if __name__ == "__main__":
    asyncio.run(main())
