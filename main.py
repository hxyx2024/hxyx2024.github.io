import os
import random
import asyncio
import re
import json
import traceback
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"
LAST_ID_FILE = "last_msg_id.json"

CANDIDATE_POOL_SIZE = 10   # 候选池最新10条（按期号）
MIN_TAKE = 3
MAX_TAKE = 6
INIT_FETCH_LIMIT = 200

# ========== 工具函数 ==========
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

def load_last_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_msg_id', 0)
        except:
            return 0
    return 0

def save_last_id(msg_id):
    with open(LAST_ID_FILE, 'w') as f:
        json.dump({'last_msg_id': msg_id}, f)

def reset_last_id():
    if os.path.exists(LAST_ID_FILE):
        os.remove(LAST_ID_FILE)

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

def is_auto_time():
    now = datetime.now(BEIJING_TZ)
    hour, minute = now.hour, now.minute
    if hour < 18 or hour > 21:
        return False
    if hour == 21 and minute >= 20:
        return False
    return True

async def fetch_messages_since(client, min_id):
    """拉取 min_id 之后的消息，返回有效开奖列表（按期号降序）和最大消息ID"""
    valid = []  # (msg_id, text, period)
    if min_id == 0:
        async for msg in client.iter_messages(CHANNEL, limit=INIT_FETCH_LIMIT):
            if msg.text and "新澳门六合彩第" in msg.text:
                txt = msg.text.strip()
                if is_complete_lottery(txt):
                    period = get_period(txt)
                    if period:
                        valid.append((msg.id, txt, period))
    else:
        async for msg in client.iter_messages(CHANNEL, min_id=min_id):
            if msg.text and "新澳门六合彩第" in msg.text:
                txt = msg.text.strip()
                if is_complete_lottery(txt):
                    period = get_period(txt)
                    if period:
                        valid.append((msg.id, txt, period))
    # 按期号降序排序（期号大的在前）
    valid.sort(key=lambda x: x[2], reverse=True)
    max_id = max([v[0] for v in valid]) if valid else None
    return [v[1] for v in valid], max_id

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    # 自动运行时检查时间段
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # 清空逻辑：手动和自动都使用每日首次清空
    if need_auto_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        reset_last_id()
        print("今日首次运行，已清空数据文件并重置 last_msg_id")

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        print(f"本地已有 {len(local_data)} 期")

        last_id = load_last_id()
        print(f"上次处理的消息ID: {last_id}")

        all_valid, max_new_id = await fetch_messages_since(client, last_id)
        print(f"本次拉取到 {len(all_valid)} 条新有效开奖（按期号降序）")

        if max_new_id:
            print(f"最新消息ID: {max_new_id}")

        if not all_valid:
            print("无新增有效开奖，退出")
            if max_new_id:
                save_last_id(max_new_id)
            return

        # 候选池：最新10条（按期号）
        top_n = all_valid[:CANDIDATE_POOL_SIZE]
        print(f"候选池长度: {len(top_n)}，期号: {[get_period(m) for m in top_n]}")

        take = random.randint(MIN_TAKE, MAX_TAKE)
        take = min(take, len(top_n))
        selected = random.sample(top_n, take) if take > 0 else []
        print(f"随机抽取 {take} 期，期号: {[get_period(m) for m in selected]}")

        if not selected:
            print("未选中任何期号，退出")
            if max_new_id:
                save_last_id(max_new_id)
            return

        # 合并历史，去重，保留最近60期
        all_blocks = local_data + selected
        unique = {}
        for b in all_blocks:
            p = get_period(b)
            if p:
                unique[p] = b
        sorted_blocks = [unique[p] for p in sorted(unique.keys())]
        if len(sorted_blocks) > MAX_KEEP:
            sorted_blocks = sorted_blocks[-MAX_KEEP:]

        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(sorted_blocks) + "\n")

        print(f"✅ 写入完成，文件总期数: {len(sorted_blocks)}")

        if max_new_id:
            save_last_id(max_new_id)

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
