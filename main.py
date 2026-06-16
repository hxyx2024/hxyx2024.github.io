import os
import json
import random
import re
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
VERSION = "3.0"
OUT_FILE = "lottery_data_api.html"
DATA_FILE = "lottery_data.json"
USED_FILE = ".used_periods.json"
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

def load_used():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_used(used):
    with open(USED_FILE, 'w', encoding='utf-8') as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

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

def main():
    print(f"版本: {VERSION}")
    print("主程序运行中...")

    # 加载数据
    all_data = load_json()
    if not all_data:
        print("⚠️ JSON 中没有数据，请先运行 fetch_history 拉取历史数据")
        return

    print(f"JSON 中共有 {len(all_data)} 期")

    # 每天第一次运行：清空 HTML 和已用记录
    is_first_run = need_auto_clean_today()
    if is_first_run:
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        with open(USED_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("今日首次运行，已清空 HTML 和已用记录")

    # 加载已用期号
    used_periods = load_used()
    print(f"已用 {len(used_periods)} 期")

    # 获取所有期号（升序）
    all_periods = sorted([item['period'] for item in all_data])
    
    # 找出未使用的期号
    available_periods = [p for p in all_periods if p not in used_periods]
    
    if not available_periods:
        print("✅ 所有期号已全部使用完毕")
        return

    # 取最新的 10 期作为候选池（从可用期号中取最新的）
    available_periods_sorted = sorted(available_periods, reverse=True)
    latest_available = available_periods_sorted[:CANDIDATE_POOL_SIZE]
    
    if len(latest_available) < CANDIDATE_POOL_SIZE:
        print(f"可用期号不足 10 期，当前可用 {len(latest_available)} 期")
    
    # 从候选池中随机抽 2-5 期
    take = random.randint(MIN_TAKE, MAX_TAKE)
    take = min(take, len(latest_available))
    if take == 0:
        print("候选池为空，退出")
        return
    
    selected_periods = random.sample(latest_available, take)
    print(f"抽取 {take} 期，期号: {selected_periods}")

    # 获取选中期号的完整数据
    selected_items = [item for item in all_data if item['period'] in selected_periods]
    
    # 标记已用
    used_periods.extend(selected_periods)
    save_used(used_periods)
    print(f"已标记 {len(selected_periods)} 期，累计已用 {len(used_periods)} 期")

    # 读取本地已有数据
    local_data = get_local_data()
    
    # 提取选中的文本
    selected_blocks = [item['text'] for item in selected_items]
    all_blocks = local_data + selected_blocks

    # 合并、去重、排序、截断（和原代码一样）
    unique = {}
    for b in all_blocks:
        p = get_period(b)
        if p:
            unique[p] = b
    sorted_blocks = [unique[p] for p in sorted(unique.keys())]
    if len(sorted_blocks) > MAX_KEEP:
        sorted_blocks = sorted_blocks[-MAX_KEEP:]

    # 写入 HTML
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(sorted_blocks) + "\n")
    print(f"✅ 写入完成，文件总期数: {len(sorted_blocks)}")

if __name__ == "__main__":
    main()
