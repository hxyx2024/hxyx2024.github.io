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

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"          # 自动触发每日清空标志
AUTO_STOP_FILE = ".auto_stop_today"           # 自动触发无新数据停止标志
MANUAL_CLEAN_FILE = ".manual_cleaned_today"   # 手动触发当日是否已清空标志

CANDIDATE_LIMIT = 20
RANDOM_MIN = 1
RANDOM_MAX = 3

MAX_RETRIES = 3
RETRY_DELAY = 5

# 邮件配置
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "xmaec555@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email(subject, body):
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

def need_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, "r") as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, "w") as f:
        f.write(today)
    return True

def clear_auto_stop():
    if os.path.exists(AUTO_STOP_FILE):
        os.remove(AUTO_STOP_FILE)

def is_auto_stopped_today():
    if not os.path.exists(AUTO_STOP_FILE):
        return False
    with open(AUTO_STOP_FILE, "r") as f:
        date_str = f.read().strip()
    return date_str == datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

def set_auto_stop():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    with open(AUTO_STOP_FILE, "w") as f:
        f.write(today)

def is_manual_cleaned_today():
    if not os.path.exists(MANUAL_CLEAN_FILE):
        return False
    with open(MANUAL_CLEAN_FILE, "r") as f:
        date_str = f.read().strip()
    return date_str == datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

def set_manual_cleaned():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    with open(MANUAL_CLEAN_FILE, "w") as f:
        f.write(today)

period_pattern = re.compile(r"第[:\s]*(\d{7})期")
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
    try:
        msg = await client.get_messages(CHANNEL, limit=1)
        if msg and msg[0].text and "新澳门六合彩第" in msg[0].text:
            return get_period(msg[0].text)
    except Exception as e:
        print(f"获取最新期号失败: {e}")
    return 0

def get_local_latest_period():
    if not os.path.exists(OUT_FILE):
        return 0
    try:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return 0
        periods = []
        for block in content.split('\n\n'):
            block = block.strip()
            if block and is_complete_lottery(block):
                periods.append(get_period(block))
        return max(periods) if periods else 0
    except Exception as e:
        print(f"读取本地最新期号失败: {e}")
        return 0

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动: {is_manual}")

    # 手动触发：仅在当天第一次手动运行时清空
    if is_manual:
        if not is_manual_cleaned_today():
            with open(OUT_FILE, "w", encoding="utf-8") as f:
                f.write("")
            set_manual_cleaned()
            print("手动触发：当天首次，已清空原数据")
            send_email("彩票采集 - 手动触发", "手动触发（首次），已清空数据，将拉取最新开奖结果")
        else:
            print("手动触发：当天非首次，不清空，仅增量拉取")

    # 自动触发：每天首次运行清空数据并清除自动停止标志
    if not is_manual and need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，已清空原数据")
        clear_auto_stop()
        send_email("彩票采集 - 每日重置", "今日首次运行，已清空旧数据，清除停止标志")

    # 自动触发时检查是否已被停止
    if not is_manual and is_auto_stopped_today():
        print("自动触发已停止（今日无新数据），跳过")
        return

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()

        channel_latest = await get_latest_period_from_channel(client)
        local_latest = get_local_latest_period()
        print(f"本地最新期号: {local_latest}, 频道最新期号: {channel_latest}")

        if channel_latest <= local_latest:
            print("无新数据")
            if not is_manual:
                set_auto_stop()
                print("已设置自动停止标志，今天后续自动触发将跳过")
            return

        # 拉取候选消息
        msgs = await fetch_messages_with_retry(client, CANDIDATE_LIMIT)
        if not msgs:
            print("未获取到任何消息")
            return

        # 提取所有有效开奖结果
        all_valid = []
        for m in msgs:
            if m.text and "新澳门六合彩第" in m.text:
                txt = m.text.strip()
                if is_complete_lottery(txt):
                    all_valid.append(txt)

        if not all_valid:
            print("候选消息中没有有效开奖结果")
            return

        # 按期号降序排序（大→小）
        all_valid.sort(key=get_period, reverse=True)
        take = random.randint(RANDOM_MIN, RANDOM_MAX)
        new_data = all_valid[:take]
        print(f"从 {len(all_valid)} 条有效结果中，随机取 {take} 条（期号最大的前 {take} 条）")

        # 去重
        seen = set()
        unique_new = []
        for txt in new_data:
            p = get_period(txt)
            if p not in seen:
                seen.add(p)
                unique_new.append(txt)

        # 读取现有数据
        old_data = []
        if os.path.exists(OUT_FILE):
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                for block in content.split('\n\n'):
                    block = block.strip()
                    if block and is_complete_lottery(block):
                        old_data.append(block)

        # 合并去重
        exist_periods = {get_period(x) for x in old_data}
        all_data = old_data[:]
        new_added = []
        for txt in unique_new:
            p = get_period(txt)
            if p not in exist_periods:
                exist_periods.add(p)
                all_data.append(txt)
                new_added.append(p)

        all_data.sort(key=get_period)   # 升序
        if len(all_data) > MAX_KEEP:
            all_data = all_data[-MAX_KEEP:]

        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_data) + "\n")

        print(f"完成，总期数 {len(all_data)}，新增 {len(new_added)} 期，新增期号: {new_added}")
        if new_added:
            send_email("彩票采集 - 采集完成", f"新增 {len(new_added)} 期，当前总期数 {len(all_data)}")

    except Exception as e:
        error_msg = f"运行失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
    finally:
        if client:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
