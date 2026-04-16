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
CLEAN_FLAG_FILE = ".last_clean_date"

# 自动触发配置
AUTO_RANDOM_MIN = 1
AUTO_RANDOM_MAX = 3
AUTO_FETCH_LIMIT_FULL = 60   # 全量拉取时最多拉取条数（手动拉取全部新数据时使用）

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5

# 邮件配置（可选）
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "xmaec555@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ========== 辅助函数 ==========
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
    """返回 True 表示今天是首次运行（需要清空）"""
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
    """从本地文件中读取最新期号（最大值）"""
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

# ========== 采集核心 ==========
async def fetch_new_data(client, local_latest):
    """
    从频道拉取所有比 local_latest 更新的有效开奖结果。
    返回列表（按期号升序），可能为空。
    """
    # 一次拉取较多消息（比如 200 条）覆盖新数据
    limit = 200
    msgs = await fetch_messages_with_retry(client, limit)
    if not msgs:
        return []
    new_data = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                p = get_period(txt)
                if p > local_latest:
                    new_data.append(txt)
    # 去重（按期号）
    seen = set()
    unique = []
    for txt in new_data:
        p = get_period(txt)
        if p not in seen:
            seen.add(p)
            unique.append(txt)
    unique.sort(key=get_period)  # 升序
    return unique

async def fetch_random_messages(client, limit):
    """拉取最新 limit 条消息，返回有效结果列表"""
    msgs = await fetch_messages_with_retry(client, limit)
    if not msgs:
        return []
    valid = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                valid.append(txt)
    # 去重
    seen = set()
    unique = []
    for txt in valid:
        p = get_period(txt)
        if p not in seen:
            seen.add(p)
            unique.append(txt)
    return unique

# ========== 手动触发 ==========
async def manual_mode():
    print("手动触发模式")
    # 检查是否需要清空
    if need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，已清空原数据")
        send_email("彩票采集 - 手动触发", "手动触发且为今日首次运行，已清空数据")
    else:
        print("今日非首次运行，不清空，仅追加新数据")

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()
        # 获取本地最新期号
        local_latest = get_local_latest_period()
        print(f"本地最新期号: {local_latest}")
        # 获取频道最新期号
        channel_latest = await get_latest_period_from_channel(client)
        print(f"频道最新期号: {channel_latest}")
        if channel_latest <= local_latest:
            print("无新数据，跳过")
            send_email("彩票采集 - 手动跳过", f"无新数据 (本地最新{local_latest}, 频道最新{channel_latest})")
            return
        # 拉取所有新数据
        new_data = await fetch_new_data(client, local_latest)
        if not new_data:
            print("未获取到新数据")
            return
        print(f"获取到新数据 {len(new_data)} 期")
        # 读取现有数据
        old_data = []
        if os.path.exists(OUT_FILE) and not need_clean_today():  # 如果不是首次运行，则读取旧数据
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
        for txt in new_data:
            p = get_period(txt)
            if p not in exist_periods:
                exist_periods.add(p)
                all_data.append(txt)
        all_data.sort(key=get_period)
        if len(all_data) > MAX_KEEP:
            all_data = all_data[-MAX_KEEP:]
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_data) + "\n")
        print(f"手动触发完成，总期数 {len(all_data)}，新增 {len(new_data)} 期")
        send_email("彩票采集 - 手动完成", f"手动触发完成，新增 {len(new_data)} 期，总期数 {len(all_data)}")
    except Exception as e:
        error_msg = f"手动触发失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
    finally:
        if client:
            await client.disconnect()

# ========== 自动触发 ==========
def is_auto_time():
    """判断当前时间是否在采集时段（北京时间 18:00-21:10）"""
    now = datetime.now(BEIJING_TZ)
    hour = now.hour
    minute = now.minute
    # 18:00 - 21:10 之间（不包括 21:10 本身）
    if hour == 21 and minute >= 10:
        return False
    if hour >= 18 and hour < 21:
        return True
    if hour == 21 and minute < 10:
        return True
    return False

async def auto_mode():
    print("自动触发模式")
    if not is_auto_time():
        print("不在采集时段 (18:00-21:10 北京时间)，退出")
        return

    # 每日首次清空
    if need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，清空旧内容")
        send_email("彩票采集 - 每日重置", "今日首次运行，已清空旧数据")

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()
        # 检查是否有新数据
        local_latest = get_local_latest_period()
        channel_latest = await get_latest_period_from_channel(client)
        print(f"本地最新期号: {local_latest}, 频道最新期号: {channel_latest}")
        if channel_latest <= local_latest:
            print("无新数据，跳过")
            return
        # 随机拉取 1-3 条最新消息
        limit = random.randint(AUTO_RANDOM_MIN, AUTO_RANDOM_MAX)
        print(f"本次随机拉取 {limit} 条")
        new_data = await fetch_random_messages(client, limit)
        if not new_data:
            print("未获取到有效数据")
            return
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
        for txt in new_data:
            p = get_period(txt)
            if p not in exist_periods:
                exist_periods.add(p)
                all_data.append(txt)
                new_added.append(p)
        all_data.sort(key=get_period)
        if len(all_data) > MAX_KEEP:
            all_data = all_data[-MAX_KEEP:]
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_data) + "\n")
        print(f"自动触发完成，总期数 {len(all_data)}，新增 {len(new_added)} 期")
        if new_added:
            send_email("彩票采集 - 自动采集", f"自动采集完成，新增 {len(new_added)} 期，当前总期数 {len(all_data)}")
    except Exception as e:
        error_msg = f"自动触发失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
    finally:
        if client:
            await client.disconnect()

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动: {is_manual}")
    if is_manual:
        await manual_mode()
    else:
        await auto_mode()

if __name__ == "__main__":
    asyncio.run(main())
