import os
import json
import random
import re
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
VERSION = "3.0"
OUT_FILE = "lottery_data_api.html"
DATA_FILE = "lottery_data.json"
MAX_KEEP = 100
BEIJING_TZ = timezone(timedelta(hours=8))
CLEAN_FLAG_FILE = ".last_clean_date_main"

CANDIDATE_POOL_SIZE = 10
MIN_TAKE = 2
MAX_TAKE = 5

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

def load_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

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
        with open(CLEAN_FLAG_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w', encoding='utf-8') as f:
        f.write(today)
    return True

def get_candidate_pool(all_data, local_periods):
    """取最新 10 期，排除已用的，不足时往前补到 10 期"""
    
    # 数据已经是升序，最新的在最后
    if len(all_data) <= CANDIDATE_POOL_SIZE:
        latest_10 = all_data[:]
    else:
        latest_10 = all_data[-CANDIDATE_POOL_SIZE:]
    
    # 排除已用的
    available = [item for item in latest_10 if item['period'] not in local_periods]
    
    # 如果不足 10 期，往前补更旧的
    if len(available) < CANDIDATE_POOL_SIZE:
        older = all_data[:-CANDIDATE_POOL_SIZE] if len(all_data) > CANDIDATE_POOL_SIZE else []
        for item in reversed(older):
            if item['period'] not in local_periods:
                available.append(item)
                if len(available) >= CANDIDATE_POOL_SIZE:
                    break
    
    # 按期号升序排列
    available.sort(key=lambda x: x['period'])
    return available

def main():
    print(f"版本: {VERSION}")
    print("主程序运行中...")

    all_data = load_json()
    if not all_data:
        print("⚠️ JSON 中没有数据，请先运行 fetch_history 拉取历史数据")
        return

    print(f"JSON 中共有 {len(all_data)} 期")

    is_first_run = need_auto_clean_today()
    
    local_data = get_local_data()
    local_periods = {get_period(b) for b in local_data}
    print(f"本地已有 {len(local_data)} 期")

    # ===== 每天第一次运行：取最新 3 期 =====
    if is_first_run:
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        print("今日首次运行，已清空 HTML 文件")

        latest_3 = all_data[-3:] if len(all_data) >= 3 else all_data
        selected_blocks = [item['text'] for item in latest_3]
        print(f"首次运行，取最新 3 期: {[item['period'] for item in latest_3]}")

        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(selected_blocks) + "\n")
        print(f"✅ 写入完成，共 {len(selected_blocks)} 期")
        return

    # ===== 后续运行：从候选池随机抽 2-5 期 =====
    available = get_candidate_pool(all_data, local_periods)

    if not available:
        print("✅ 候选池为空，所有期号已全部使用完毕")
        return

    print(f"候选池共 {len(available)} 期")
    if len(available) < CANDIDATE_POOL_SIZE:
        print(f"可用期号不足 10 期，当前可用 {len(available)} 期")

    take = random.randint(MIN_TAKE, MAX_TAKE)
    take = min(take, len(available))
    if take == 0:
        print("候选池为空，退出")
        return

    selected = random.sample(available, take)
    selected_periods = [item['period'] for item in selected]
    print(f"抽取 {take} 期，期号: {selected_periods}")

    selected_blocks = [item['text'] for item in selected]
    all_blocks = local_data + selected_blocks

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

if __name__ == "__main__":
    main()
