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
AUTO_STOP_FILE = ".auto_stop_today"

CANDIDATE_POOL_SIZE = 10   # 固定候选池大小
MAX_TAKE = 3               # 单次最大采集条数
FETCH_LIMIT = 200          # 拉取消息数量

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
    return [block for block in content.split('\n\n') if is_complete_lottery(block)]

def need_clean_today():
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

def is_auto_stopped_today():
    if not os.path.exists(AUTO_STOP_FILE):
        return False
    with open(AUTO_STOP_FILE, 'r') as f:
        return f.read().strip() == datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

def set_auto_stop():
    with open(AUTO_STOP_FILE, 'w') as f:
        f.write(datetime.now(BEIJING_TZ).strftime("%Y-%m-%d"))

def clear_auto_stop():
    if os.path.exists(AUTO_STOP_FILE):
        os.remove(AUTO_STOP_FILE)

async def get_recent_valid_messages(client, limit=FETCH_LIMIT):
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

    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # 每日清空（仅自动）
    if not is_manual and need_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        if os.path.exists(AUTO_STOP_FILE):
            os.remove(AUTO_STOP_FILE)
        print("今日首次自动运行，已清空数据及自动停止标记")

    if not is_manual and is_auto_stopped_today():
        print("自动触发已停止（今日无新数据）")
        return

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        is_first_run = (len(local_data) == 0)
        print(f"本地数据: {len(local_data)} 期，首次运行: {is_first_run}")

        all_valid = await get_recent_valid_messages(client, limit=FETCH_LIMIT)
        print(f"有效开奖总数: {len(all_valid)}")

        if not all_valid:
            print("无有效开奖消息")
            if not is_manual:
                set_auto_stop()
            return

        # ===== 强制候选池切片 =====
        top_n = all_valid[:CANDIDATE_POOL_SIZE]
        print(f"候选池实际长度: {len(top_n)} (期望 ≤ {CANDIDATE_POOL_SIZE})")
        if len(top_n) > CANDIDATE_POOL_SIZE:
            raise RuntimeError(f"候选池长度异常: {len(top_n)} > {CANDIDATE_POOL_SIZE}")

        # ===== 选取逻辑 =====
        if is_first_run:
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(top_n))
            selected = top_n[:take]   # 关键切片，只取前 take 条
            print(f"首次运行，取候选池前 {take} 条")
        else:
            candidates = [msg for msg in top_n if get_period(msg) not in local_periods]
            print(f"过滤后剩余候选: {len(candidates)}")
            if not candidates:
                print("无新期号")
                if not is_manual:
                    set_auto_stop()
                return
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(candidates))
            selected = random.sample(candidates, take)
            print(f"后续运行，随机抽取 {take} 条")

        # ===== 最终数量校验 =====
        if len(selected) > MAX_TAKE:
            raise RuntimeError(f"选取数量超限: {len(selected)} > {MAX_TAKE}")

        selected_periods = [get_period(m) for m in selected]
        print(f"选中期号: {selected_periods}")

        # ===== 合并去重写入 =====
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

        if not is_manual:
            clear_auto_stop()

    except Exception as e:
        print(f"严重错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
