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
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date"

FETCH_LIMIT = 200
CANDIDATE_POOL_SIZE = 10
MIN_TAKE = 1
MAX_TAKE = 3

# ========== 彩种配置 ==========
LOTTERIES = {
    "laoao": {
        "out_file": "laoao_lottery_data.html",
        "period_pattern": re.compile(r"老澳21\.30第[:\s]*(\d{7})\s*期"),
        "name": "老澳"
    },
    "hk": {
        "out_file": "hk_lottery_data.html",
        "period_pattern": re.compile(r"香港六合彩第[:\s]*(\d{7})期"),
        "name": "香港"
    }
}

# ========== 工具函数 ==========
def get_period(text, pattern):
    m = pattern.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text, pattern):
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 4:
        return False
    if not re.search(r'\d+\s+\d+', lines[1]):
        return False
    if not re.search(r'[鼠牛虎兔龍蛇馬羊猴雞狗豬]', lines[2]):
        return False
    if not re.search(r'[🟢🔴🔵]', lines[3]):
        return False
    if not pattern.search(lines[0]):
        return False
    return True

def get_local_data(out_file, pattern):
    if not os.path.exists(out_file):
        return []
    with open(out_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    blocks = content.split('\n\n')
    valid = []
    seen = set()
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        p = get_period(b, pattern)
        if p and p not in seen:
            seen.add(p)
            valid.append(b)
    valid.sort(key=lambda x: get_period(x, pattern))
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

async def fetch_recent_messages(client, limit, pattern):
    items = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt, pattern):
                period = get_period(txt, pattern)
                if period:
                    items.append((period, txt))
    items.sort(key=lambda x: x[0], reverse=True)
    return [txt for _, txt in items]

def clean_state_files():
    state_files = ["ga_gb_state.json", "last_msg_id.json", "default_rules_state.json"]
    for sf in state_files:
        if os.path.exists(sf):
            os.remove(sf)
            print(f"已删除状态文件 {sf}")

async def process_lottery(client, lottery_key, lottery_config, is_first_run):
    out_file = lottery_config["out_file"]
    pattern = lottery_config["period_pattern"]
    name = lottery_config["name"]
    
    print(f"\n--- 开始处理 {name} 彩 ---")
    
    local_data = get_local_data(out_file, pattern)
    local_periods = {get_period(b, pattern) for b in local_data}
    print(f"本地已有 {len(local_data)} 期")
    
    all_valid = await fetch_recent_messages(client, FETCH_LIMIT, pattern)
    print(f"从最近 {FETCH_LIMIT} 条消息中提取到 {len(all_valid)} 条有效开奖（按期号降序）")
    
    if not all_valid:
        print("未拉取到任何有效开奖，退出")
        return
    
    new_periods = [txt for txt in all_valid if get_period(txt, pattern) not in local_periods]
    print(f"新期号数量: {len(new_periods)}")
    
    if not new_periods:
        print("无新期号，退出")
        return
    
    pool = new_periods[:CANDIDATE_POOL_SIZE]
    take = random.randint(MIN_TAKE, MAX_TAKE)
    take = min(take, len(pool))
    if take == 0:
        print("候选池为空，退出")
        return
    selected = random.sample(pool, take)
    print(f"抽取 {take} 期，期号: {[get_period(t, pattern) for t in selected]}")
    
    all_blocks = local_data + selected
    unique = {}
    for b in all_blocks:
        p = get_period(b, pattern)
        if p:
            unique[p] = b
    sorted_blocks = [unique[p] for p in sorted(unique.keys())]
    if len(sorted_blocks) > MAX_KEEP:
        sorted_blocks = sorted_blocks[-MAX_KEEP:]
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(sorted_blocks) + "\n")
    print(f"✅ {name} 彩写入完成，文件总期数: {len(sorted_blocks)}")

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")
    
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return
    
    client = await TelegramClient("session", API_ID, API_HASH).start()
    
    try:
        is_first_run = need_auto_clean_today()
        if is_first_run:
            for cfg in LOTTERIES.values():
                with open(cfg["out_file"], 'w', encoding='utf-8') as f:
                    f.write('')
                print(f"今日首次运行，已清空数据文件 {cfg['out_file']}")
            clean_state_files()
        
        for key, cfg in LOTTERIES.items():
            await process_lottery(client, key, cfg, is_first_run)
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
