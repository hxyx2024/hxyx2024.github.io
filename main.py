import os
import random
import asyncio
import re
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

FETCH_LIMIT = 200
CANDIDATE_POOL_SIZE = 10
MIN_TAKE = 3
MAX_TAKE = 6

# ========== 工具函数 ==========
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
    hour = now.hour
    if hour < 18 or hour > 21:
        return False
    if hour == 21 and now.minute >= 20:
        return False
    return True

async def fetch_recent_messages(client, limit):
    items = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if msg.text and "新澳门六合彩第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                period = get_period(txt)
                if period:
                    items.append((period, txt))
    items.sort(key=lambda x: x[0], reverse=True)  # 按期号降序
    return [txt for _, txt in items]

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    # 自动运行时检查时间段
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        # 读取本地已有数据
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        print(f"本地已有 {len(local_data)} 期")

        # 拉取最近 FETCH_LIMIT 条消息
        all_valid = await fetch_recent_messages(client, FETCH_LIMIT)
        print(f"从最近 {FETCH_LIMIT} 条消息中提取到 {len(all_valid)} 条有效开奖（按期号降序）")

        if not all_valid:
            print("未拉取到任何有效开奖，退出")
            return

        # 筛选出新期号
        new_periods = [txt for txt in all_valid if get_period(txt) not in local_periods]
        print(f"新期号数量: {len(new_periods)}")

        if not new_periods:
            print("无新期号，退出")
            return

        # 自动运行且今日首次 -> 清空文件，只取最新3期
        if not is_manual and need_auto_clean_today():
            print("自动运行：今日首次，清空文件并只取最新3期")
            # 取最新3期（new_periods 已是降序，前3条即最新）
            take = min(3, len(new_periods))
            selected = new_periods[:take]
            # 直接写入，不循环
            with open(OUT_FILE, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(selected) + "\n")
            print(f"✅ 写入完成，共 {len(selected)} 期")
            # 注意：不更新 last_clean_date 已在 need_auto_clean_today 中更新
            return

        # 手动运行 或 自动非首次 -> 循环抽取
        print("进入循环抽取模式")
        current_data = local_data.copy()
        current_periods = local_periods.copy()
        remaining = new_periods[:]   # 剩余新期号（降序）

        while remaining and len(current_data) < MAX_KEEP:
            pool = remaining[:CANDIDATE_POOL_SIZE]
            if not pool:
                break

            max_can_take = MAX_KEEP - len(current_data)
            take = random.randint(MIN_TAKE, MAX_TAKE)
            take = min(take, len(pool), max_can_take)
            if take == 0:
                break

            selected = random.sample(pool, take)
            for txt in selected:
                p = get_period(txt)
                if p not in current_periods:
                    current_periods.add(p)
                    current_data.append(txt)

            # 从剩余列表中移除已选中的
            remaining = [txt for txt in remaining if txt not in selected]

            # 如果超出60期，截断
            if len(current_data) > MAX_KEEP:
                current_data.sort(key=get_period)
                current_data = current_data[-MAX_KEEP:]
                current_periods = {get_period(b) for b in current_data}

            print(f"本轮抽取 {take} 期，当前文件期数: {len(current_data)}")

            if len(current_data) >= MAX_KEEP:
                print("文件已达60期上限，停止")
                break

        # 最终写回文件
        current_data.sort(key=get_period)   # 升序保存
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(current_data) + "\n")
        print(f"✅ 写入完成，文件总期数: {len(current_data)}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
