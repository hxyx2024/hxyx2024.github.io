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
MAX_KEEP = 60                     # 自动触发时最多保留60期
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"

# 手动触发配置
MANUAL_TARGET = 30                # 手动触发目标期数
MANUAL_FETCH_LIMIT = 500          # 手动触发拉取消息数量（确保覆盖30期）

# 自动触发重试配置
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

# ========== 手动触发逻辑 ==========
async def manual_mode():
    """手动触发：清空文件，拉取最新的 MANUAL_TARGET 期开奖结果"""
    print("手动触发模式")
    # 清空原文件
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("")
    print("已清空原数据")
    send_email("彩票采集 - 手动触发", f"手动触发，将采集最新的 {MANUAL_TARGET} 期")

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()
        # 拉取足够多的消息
        msgs = await fetch_messages_with_retry(client, MANUAL_FETCH_LIMIT)
        if not msgs:
            print("未拉取到任何消息")
            return
        # 筛选有效开奖结果
        valid = []
        for m in msgs:
            if m.text and "新澳门六合彩第" in m.text:
                txt = m.text.strip()
                if is_complete_lottery(txt):
                    valid.append(txt)
        # 去重（按期号）
        seen = set()
        unique = []
        for txt in valid:
            p = get_period(txt)
            if p not in seen:
                seen.add(p)
                unique.append(txt)
        # 按期号降序排序，取前 MANUAL_TARGET 条
        unique.sort(key=get_period, reverse=True)
        top = unique[:MANUAL_TARGET]
        # 按期号升序写入（与原有格式一致）
        top.sort(key=get_period)
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(top) + "\n")
        print(f"手动触发完成，共写入 {len(top)} 期")
        send_email("彩票采集 - 手动完成", f"手动触发完成，共采集 {len(top)} 期（最新 {MANUAL_TARGET} 期）")
    except Exception as e:
        error_msg = f"手动触发失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
    finally:
        if client:
            await client.disconnect()

# ========== 自动触发逻辑 ==========
def get_auto_limit():
    """根据当前时间返回自动采集条数"""
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

async def get_latest_period_from_channel(client):
    try:
        msg = await client.get_messages(CHANNEL, limit=1)
        if msg and msg[0].text and "新澳门六合彩第" in msg[0].text:
            return get_period(msg[0].text)
    except Exception as e:
        print(f"获取最新期号失败: {e}")
    return 0

async def auto_mode():
    """自动触发：根据时段采集，去重合并，保留最近 MAX_KEEP 期"""
    print("自动触发模式")
    # 每日首次清空
    if need_clean_today():
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print("今日首次运行，清空旧内容")
        send_email("彩票采集 - 每日重置", "今日首次运行，已清空旧数据")

    limit = get_auto_limit()
    if limit == 0:
        print("不在采集时段，退出")
        return
    print(f"本次采集 {limit} 条")

    # 21:10 智能跳过
    if limit == 60:
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
            await temp_client.start()
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
        await client.start()
        msgs = await fetch_messages_with_retry(client, limit)
        await client.disconnect()
    except Exception as e:
        error_msg = f"自动触发拉取失败: {type(e).__name__}: {e}"
        print(error_msg)
        traceback.print_exc()
        send_email("彩票采集 - 错误", error_msg)
        if client:
            await client.disconnect()
        return

    # 提取新数据
    new_data = []
    for m in msgs:
        if m.text and "新澳门六合彩第" in m.text:
            txt = m.text.strip()
            if is_complete_lottery(txt):
                new_data.append(txt)
    new_data.sort(key=get_period, reverse=True)

    # 读取旧数据
    old = []
    if os.path.exists(OUT_FILE):
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
        if limit == 60:
            send_email("彩票采集 - 全量完成", f"21:10 全量采集完成，现有 {len(all_data)} 期，新增 {len(new_added)} 期")
        elif new_added:
            send_email("彩票采集 - 随机采集", f"随机采集完成，新增 {len(new_added)} 期，当前总期数 {len(all_data)}")
    except Exception as e:
        error_msg = f"写入文件失败: {e}"
        print(error_msg)
        send_email("彩票采集 - 错误", error_msg)

# ========== 主入口 ==========
async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"事件: {os.environ.get('GITHUB_EVENT_NAME')}, 手动: {is_manual}")
    if is_manual:
        await manual_mode()
    else:
        await auto_mode()

if __name__ == "__main__":
    asyncio.run(main())
