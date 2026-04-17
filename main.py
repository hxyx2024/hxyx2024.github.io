import os
import asyncio
import re
import traceback
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"
INIT_FETCH_LIMIT = 4

period_pattern = re.compile(r"新澳门六合彩第[:\s]*(\d{7})期")

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

def get_local_data():
    if not os.path.exists(OUT_FILE):
        return []
    with open(OUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    blocks = content.split('\n\n')
    valid = []
    seen = set()
    for b in blocks:
        b = b.strip()
        if b.startswith('<!--'):
            continue
        if not b or not is_complete_lottery(b):
            continue
        p = get_period(b)
        if p and p not in seen:
            seen.add(p)
            valid.append(b)
    valid.sort(key=get_period)
    return valid

def need_auto_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w') as f:
        f.write(today)
    return True

async def fetch_recent_messages(client, limit):
    """只取最新的 N 条有效开奖（绝对可靠）"""
    valid = []
    messages = await client.get_messages(CHANNEL, limit=limit)
    # 倒序，保证从旧到新
    messages = reversed(messages)
    for msg in messages:
        if msg.text and "第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                valid.append(txt)
                if len(valid) >= limit:
                    break
    return valid

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    # 清空文件（物理清空）
    if is_manual:
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        print("手动触发：已清空数据文件")
        print(f"清空验证：文件大小 = {os.path.getsize(OUT_FILE)} 字节 (应为0)")
    else:
        if need_auto_clean_today():
            with open(OUT_FILE, 'w', encoding='utf-8') as f:
                f.write('')
            print("自动触发：今日首次运行，已清空数据文件")
            print(f"清空验证：文件大小 = {os.path.getsize(OUT_FILE)} 字节 (应为0)")
        else:
            print("自动触发：今日已清空过，不再清空")

    client = await TelegramClient("session", API_ID, API_HASH).start()
    try:
        # 关键：手动模式完全不读取旧数据
        if is_manual:
            local_data = []
            print("手动模式：忽略所有本地旧数据")
        else:
            local_data = get_local_data()
            print(f"自动模式：本地已有 {len(local_data)} 期")

        local_periods = {get_period(b) for b in local_data}

        all_valid = await fetch_recent_messages(client, INIT_FETCH_LIMIT)
        print(f"从最近 {INIT_FETCH_LIMIT} 条消息中提取到 {len(all_valid)} 条有效开奖")

        if not all_valid:
            print("未拉取到任何有效开奖，退出")
            return

        # 找出新期号（相对于 local_data）
        new_periods = []
        for txt in all_valid:
            p = get_period(txt)
            if p and p not in local_periods:
                new_periods.append(txt)
        print(f"新期号数量: {len(new_periods)}")

        if not new_periods:
            print("无新期号，退出")
            return

        all_blocks = local_data + new_periods
        unique = {}
        for b in all_blocks:
            p = get_period(b)
            if p:
                unique[p] = b
        sorted_blocks = [unique[p] for p in sorted(unique.keys())]
        if len(sorted_blocks) > MAX_KEEP:
            sorted_blocks = sorted_blocks[-MAX_KEEP:]

        # 构建文件内容
        content = "\n\n".join(sorted_blocks) + "\n"
        if is_manual:
            timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
            content += f"<!-- 手动更新于 {timestamp} (北京时间) -->\n"

        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 写入完成，文件总期数: {len(sorted_blocks)}，文件大小: {os.path.getsize(OUT_FILE)} 字节")
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
