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
CLEAN_FLAG_FILE = ".last_clean_date"   # 仅用于记录自动清空日期

CANDIDATE_POOL_SIZE = 10   # 候选池固定最新 10 条
MAX_TAKE = 3               # 单次最多采集 3 条
FETCH_LIMIT = 200          # 每次拉取消息数

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
    """读取本地数据文件，返回有效开奖文本列表（按读取顺序，后续会统一排序）"""
    if not os.path.exists(OUT_FILE):
        return []
    with open(OUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    return [block for block in content.split('\n\n') if is_complete_lottery(block)]

def need_auto_clean_today():
    """
    检查今天是否已执行过自动清空。
    仅当触发方式为自动时才调用此函数。
    基于北京时间判断日期。
    """
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r') as f:
            if f.read().strip() == today:
                return False
    # 记录今天已清空，并返回 True
    with open(CLEAN_FLAG_FILE, 'w') as f:
        f.write(today)
    return True

def is_auto_time():
    """判断当前北京时间是否在自动触发时段（18:00-21:20）"""
    now = datetime.now(BEIJING_TZ)
    hour, minute = now.hour, now.minute
    if hour < 18 or hour > 21:
        return False
    if hour == 21 and minute >= 20:
        return False
    return True

async def get_recent_valid_messages(client, limit=FETCH_LIMIT):
    """获取最近 limit 条消息中的有效开奖文本（降序，最新在前）"""
    valid = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if msg.text and "新澳门六合彩第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                valid.append(txt)
    return valid

# ========== 主逻辑 ==========
async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    # 自动时段限制
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # ----- 自动每日清空（仅自动触发） -----
    if not is_manual and need_auto_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        print("今日首次自动运行，已清空数据文件")

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        # 1. 读取本地数据
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        is_first_run = (len(local_data) == 0)
        print(f"本地已有 {len(local_data)} 期，是否首次运行: {is_first_run}")

        # 2. 拉取有效开奖
        all_valid = await get_recent_valid_messages(client, limit=FETCH_LIMIT)
        print(f"拉取 {FETCH_LIMIT} 条消息，有效开奖 {len(all_valid)} 期")

        if not all_valid:
            print("无有效开奖消息，退出")
            return

        # 3. 候选池（最新 10 条）
        top_n = all_valid[:CANDIDATE_POOL_SIZE]
        print(f"候选池长度: {len(top_n)} (期望 ≤ {CANDIDATE_POOL_SIZE})")
        if len(top_n) > CANDIDATE_POOL_SIZE:
            raise RuntimeError(f"候选池长度异常: {len(top_n)} > {CANDIDATE_POOL_SIZE}")

        # 4. 选取新数据
        if is_first_run:
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(top_n))
            selected = top_n[:take]          # 取最新 take 条
            print(f"首次运行，取最新 {take} 期")
        else:
            candidates = [msg for msg in top_n if get_period(msg) not in local_periods]
            print(f"过滤本地后剩余候选: {len(candidates)} 条")
            if not candidates:
                print("候选池中无新期号，退出")
                return
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(candidates))
            selected = random.sample(candidates, take)
            print(f"后续运行，随机抽取 {take} 期")

        if len(selected) > MAX_TAKE:
            raise RuntimeError(f"选取数量异常: {len(selected)} > {MAX_TAKE}")

        selected_periods = [get_period(m) for m in selected]
        print(f"选中期号: {selected_periods}")

        # 5. 合并、去重、排序、保留最近 MAX_KEEP 期
        all_blocks = local_data + selected
        unique = {}
        for block in all_blocks:
            p = get_period(block)
            if p:
                unique[p] = block

        sorted_blocks = [unique[p] for p in sorted(unique.keys())]
        if len(sorted_blocks) > MAX_KEEP:
            sorted_blocks = sorted_blocks[-MAX_KEEP:]

        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(sorted_blocks) + "\n")

        print(f"写入完成，文件总期数: {len(sorted_blocks)}")

    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
