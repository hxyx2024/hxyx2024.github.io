from telethon import TelegramClient
import asyncio
import re

API_ID = 3608828
API_HASH = "7b78971ae31f48f666c2148c761cca41"
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60

period_pattern = re.compile(r"第[:\s]*(\d+)期")

def get_period(text):
    match = period_pattern.search(text)
    if match:
        return int(match.group(1))
    else:
        # 调试：打印无法提取期数的消息开头
        print(f"⚠️ 警告：无法提取期数 -> {text[:60]}")
        return 0

def is_complete_lottery(text):
    lines = text.strip().split('\n')
    # 过滤掉空行后计算有效行数
    effective_lines = [line for line in lines if line.strip()]
    return len(effective_lines) >= 4

async def main():
    # 直接覆盖写入，不读取旧文件（彻底清空）
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    # 多取一些消息，确保能凑够60期完整记录（频道每天一期，取150条足够）
    messages = await client.get_messages(CHANNEL, limit=150)
    await client.disconnect()

    print(f"共获取 {len(messages)} 条消息")

    complete_lotteries = []
    for msg in messages:
        if msg.text and "新澳门六合彩第" in msg.text:
            full_text = msg.text.strip()
            if is_complete_lottery(full_text):
                period = get_period(full_text)
                if period > 0:
                    complete_lotteries.append(full_text)
                    print(f"✅ 有效期 {period}")
                else:
                    print(f"❌ 期号无效: {full_text[:50]}")
            else:
                print(f"❌ 不完整（行数不足）: {full_text[:50]}")

    print(f"完整且期号有效的消息数: {len(complete_lotteries)}")

    if not complete_lotteries:
        print("错误：没有采集到任何完整开奖消息，请检查频道名称或消息格式。")
        return

    # 按期数降序排序
    complete_lotteries.sort(key=get_period, reverse=True)

    # 按期号去重（保留第一次出现的，即期数大的在前）
    seen = set()
    unique = []
    for item in complete_lotteries:
        p = get_period(item)
        if p not in seen:
            seen.add(p)
            unique.append(item)

    # 只保留最新 MAX_KEEP 期
    if len(unique) > MAX_KEEP:
        unique = unique[:MAX_KEEP]

    # 覆盖写入文件
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(unique) + "\n")

    print(f"✅ 采集完成 | 共保存 {len(unique)} 期（已清空旧内容，从大到小排列）")

if __name__ == "__main__":
    asyncio.run(main())
