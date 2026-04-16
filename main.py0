from telethon import TelegramClient
import asyncio
import re

# 配置
API_ID = 3608828
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60  # 只保留最新60期

# 匹配期数
period_pattern = re.compile(r"第:(\d+)期")

def get_period(text):
    match = period_pattern.search(text)
    return int(match.group(1)) if match else 0

async def main():
    # ----------------------
    # 第一次运行：清空旧内容
    # ----------------------
    try:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            existing = f.read().strip()
    except FileNotFoundError:
        existing = ""

    if not existing:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("🗑️ 首次运行，已清空旧内容")

    # ----------------------
    # 从最新期开始采集
    # ----------------------
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    messages = await client.get_messages(CHANNEL, limit=60)
    await client.disconnect()

    # 提取有效开奖信息
    new_data = []
    for msg in messages:
        if msg.text and "新澳门六合彩第" in msg.text:
            new_data.append(msg.text.strip())

    # ----------------------
    # 排序：小期在上，大期在最后
    # ----------------------
    new_data = sorted(new_data, key=lambda x: get_period(x))

    # ----------------------
    # 读取旧内容
    # ----------------------
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        old_lines = [l.strip() for l in f if l.strip()]

    # ----------------------
    # 合并 + 去重
    # ----------------------
    all_lines = []
    seen = set()
    for line in old_lines + new_data:
        if line not in seen:
            seen.add(line)
            all_lines.append(line)

    # ----------------------
    # 再次排序 + 只保留60条
    # ----------------------
    all_lines = sorted(all_lines, key=lambda x: get_period(x))
    all_lines = all_lines[-MAX_KEEP:]

    # ----------------------
    # 写入最终文件
    # ----------------------
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_lines) + "\n")

    print(f"✅ 采集完成 | 当前共 {len(all_lines)} 期（保留最新60期）")

if __name__ == "__main__":
    asyncio.run(main())
