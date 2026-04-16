from telethon import TelegramClient
import asyncio
import re

# 配置
API_ID = 3608828
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60

# 匹配期数（兼容“第:数字期”或“第数字期”）
period_pattern = re.compile(r"第[:\s]*(\d+)期")

def get_period(text):
    match = period_pattern.search(text)
    return int(match.group(1)) if match else 0

def is_complete_lottery(text):
    """判断是否为完整开奖消息（至少4行）"""
    lines = text.strip().split('\n')
    return len(lines) >= 4

async def main():
    # 首次运行清空旧内容
    try:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            existing = f.read().strip()
    except FileNotFoundError:
        existing = ""

    if not existing:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("🗑️ 首次运行，已清空旧内容")

    # 连接 Telegram 并获取最新60条消息
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    messages = await client.get_messages(CHANNEL, limit=60)
    await client.disconnect()

    # 提取完整开奖信息（至少4行）
    new_data = []
    for msg in messages:
        if msg.text and "新澳门六合彩第" in msg.text:
            full_text = msg.text.strip()
            if is_complete_lottery(full_text):
                new_data.append(full_text)

    # 按期数降序排序（大期数在前，小期数在后）
    new_data = sorted(new_data, key=lambda x: get_period(x), reverse=True)

    # 读取旧内容
    try:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            old_lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        old_lines = []

    # 合并 + 按期号去重
    existing_periods = {get_period(line) for line in old_lines}
    all_lines = old_lines.copy()
    for line in new_data:
        period = get_period(line)
        if period not in existing_periods:
            existing_periods.add(period)
            all_lines.append(line)

    # 再次降序排序 + 只保留最新60期（期数最大的60条）
    all_lines = sorted(all_lines, key=lambda x: get_period(x), reverse=True)
    if len(all_lines) > MAX_KEEP:
        all_lines = all_lines[:MAX_KEEP]

    # 写入文件（每期之间空一行）
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_lines) + "\n")

    print(f"✅ 采集完成 | 当前共 {len(all_lines)} 期（从大到小排列，保留最新60期）")

if __name__ == "__main__":
    asyncio.run(main())
