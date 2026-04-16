from telethon import TelegramClient
import asyncio
import re
import random
import os
from datetime import datetime, timezone, timedelta
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ========== 从环境变量读取敏感信息 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"

MANUAL_FETCH_LIMIT = 30   # 手动触发固定采集30条
MAX_RETRIES = 3           # 最大重试次数
RETRY_DELAY = 5           # 初始重试延迟（秒）

# 邮件配置（可选）
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "xmaec555@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # 需要在 Secrets 中配置
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email(subject, body):
    """发送邮件通知"""
    if not EMAIL_PASSWORD:
        print("未配置 EMAIL_PASSWORD，跳过邮件通知")
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"邮件通知已发送: {subject}")
    except Exception as e:
        print(f"发送邮件失败: {e}")

def get_fetch_limit(is_manual):
    if is_manual:
        return MANUAL_FETCH_LIMIT
    now = datetime.now(BEIJING_TZ)
    hour = now.hour
    minute = now.minute
    if hour == 21 and minute == 10:
        return 60
    if 18 <= hour < 20:
        return random.randint(3, 5)
    if 20 <= hour < 21 or (hour == 21 and minute < 10):
        return random.randint(3, 5)
    return 0

def need_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, "r") as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, "w") as f:
        f.write(today)
    return True

period_pattern = re.compile(r"第[:\s]*(\d+)期")
def get_period(text):
    m = period_pattern.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text):
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 4:
        return False
    if not re.search(r'\d+\s+\d+', lines[1]):
        return False
    if not re.search(r'[鼠牛虎兔龍蛇馬羊猴雞狗豬]', lines[2]):
        return False
    if not re.search(r'[🟢🔴🔵]', lines[3]):
        return False
    return True

async def fetch_messages_with_retry(client, limit):
    """带重试的消息拉取，精确处理 FloodWait"""
    for attempt in range(MAX_RETRIES):
        try:
            msgs = await client.get_messages(CHANNEL, limit=limit)
            return msgs
        except Exception as e:
            error_type = type(e).__name__
            print(f"拉取消息失败 (尝试 {attempt+1}/{MAX_RETRIES}): {error_type}: {e}")
            if error_type == "FloodWaitError":
                wait_time = getattr(e, 'seconds', RETRY_DELAY * (2 ** attempt))
                print(f"触发限流，等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time + 1)
            else:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
    return []

async def get_latest_period_from_channel(client):
    """获取频道中最新一期的期号，用于智能跳过"""
    try:
        msg = await client.get_messages(CHANNEL, limit=1)
        if msg and msg[0].text and "新澳门六合彩第" in msg[0].text:
            return get_period(msg[0].text)
    except Exception as e:
        print(f"获取最新期号失败: {e}")
    return 0

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动: {is_manual}")

    # 手动触发时清空文件
    if is_manual:
        try:
            with open(OUT_FILE, "w", encoding="utf-8") as f:
                f.write("")
            print("手动触发：已清空原数据")
            send_email("彩票采集 - 手动触发", f"手动触发，清空数据并采集最新 {MANUAL_FETCH_LIMIT} 期")
        except Exception as e:
            print(f"手动触发清空文件失败: {e}")

    # 每日自动清空
    if not is_manual and need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，清空旧内容")
        send_email("彩票采集 - 每日重置", "今日首次运行，已清空旧数据")

    limit = get_fetch_limit(is_manual)
    if limit == 0:
        print("不在采集时段且非手动，退出")
        return
    print(f"本次采集 {limit} 条")

    # 21:10 智能跳过逻辑
    if limit == 60 and not is_manual:
        existing_periods = []
        if os.path.exists(OUT_FILE):
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                for block in content.split('\n\n'):
                    block = block.strip()
                    if block and is_complete_lottery(block):
                        existing_periods.append(get_period(block))
        if len(existing_periods) >= MAX_KEEP:
            temp_client = TelegramClient("session", API_ID, API_HASH)
            await temp_client.start(timeout=30)
            latest_period = await get_latest_period_from_channel(temp_client)
            await temp_client.disconnect()
            if latest_period and existing_periods and max(existing_periods) >= latest_period:
                msg = f"已有数据完整（最新期号 {max(existing_periods)} >= 频道最新 {latest_period}），跳过21:10全量采集"
                print(msg)
                send_email("彩票采集 - 智能跳过", msg)
                return

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start(timeout=30)
        msgs = await fetch_messages_with_retry(client, limit)
        await client.disconnect()
    except Exception as e:
        error_msg = f"Telegram 连接或拉取失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
        if client:
            await client.disconnect()
        return

    new_data = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                new_data.append(txt)

    new_data.sort(key=get_period, reverse=True)

    old = []
    if not is_manual and os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                for block in content.split('\n\n'):
                    block = block.strip()
                    if block and is_complete_lottery(block):
                        old.append(block)
        except Exception as e:
            print(f"读取旧文件失败: {e}")

    exist_periods = {get_period(x) for x in old}
    all_data = old[:]
    new_added = []
    for line in new_data:
        p = get_period(line)
        if p not in exist_periods:
            exist_periods.add(p)
            all_data.append(line)
            new_added.append(p)

    all_data.sort(key=get_period)
    if len(all_data) > MAX_KEEP:
        all_data = all_data[-MAX_KEEP:]

    try:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_data) + "\n")
        print(f"完成，共 {len(all_data)} 期，新增 {len(new_data)} 期，新增期号: {new_added}")
        if is_manual:
            send_email("彩票采集 - 手动完成", f"手动触发完成，共 {len(all_data)} 期（最新30条）")
        elif limit == 60:
            send_email("彩票采集 - 全量完成", f"21:10 全量采集完成，现有 {len(all_data)} 期，新增 {len(new_added)} 期")
        elif new_added:
            send_email("彩票采集 - 随机采集", f"随机采集完成，新增 {len(new_added)} 期，当前总期数 {len(all_data)}")
    except Exception as e:
        error_msg = f"写入文件失败: {e}"
        print(error_msg)
        send_email("彩票采集 - 错误", error_msg)

if __name__ == "__main__":
    asyncio.run(main())
