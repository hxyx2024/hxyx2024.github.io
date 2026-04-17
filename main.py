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
LAST_ID_FILE = "last_msg_id.json"      # 新增：记录最后处理的消息ID

CANDIDATE_POOL_SIZE = 10   # 候选池固定最新10条
MAX_TAKE = 3               # 单次最多采集3条
INIT_FETCH_LIMIT = 200     # 首次拉取消息数

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

def load_last_id():
    """加载上次处理的最大消息ID，若文件不存在或首次运行返回0"""
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_msg_id', 0)
        except:
            return 0
    return 0

def save_last_id(msg_id):
    """保存最新处理的消息ID"""
    with open(LAST_ID_FILE, 'w') as f:
        json.dump({'last_msg_id': msg_id}, f)

def reset_last_id():
    """重置消息ID（用于每日清空时）"""
    if os.path.exists(LAST_ID_FILE):
        os.remove(LAST_ID_FILE)

def get_local_data():
    """读取本地文件，返回去重且升序的有效开奖列表"""
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
    # 若发现异常，自动修复写回
    if len(valid) != len(blocks):
        print(f"⚠️ 本地文件异常，已自动修复（原 {len(blocks)} 块 → {len(valid)} 块）")
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(valid) + "\n")
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

async def fetch_messages_since(client, min_id, limit=None):
    """
    拉取 min_id 之后的消息（即 ID > min_id），返回有效开奖文本列表（降序）。
    若 min_id == 0，则拉取最近 limit 条消息（用于初始化）。
    """
    valid = []
    if min_id == 0:
        # 首次运行：拉取最近 INIT_FETCH_LIMIT 条
        async for msg in client.iter_messages(CHANNEL, limit=INIT_FETCH_LIMIT):
            if msg.text and "新澳门六合彩第" in msg.text:
                txt = msg.text.strip()
                if is_complete_lottery(txt):
                    valid.append((msg.id, txt))
    else:
        # 后续增量：拉取所有 ID > min_id 的消息
        async for msg in client.iter_messages(CHANNEL, min_id=min_id):
            if msg.text and "新澳门六合彩第" in msg.text:
                txt = msg.text.strip()
                if is_complete_lottery(txt):
                    valid.append((msg.id, txt))
    # 按消息ID降序排列（ID越大越新）
    valid.sort(key=lambda x: x[0], reverse=True)
    return [txt for _, txt in valid], max([id for id, _ in valid]) if valid else None

# ========== 主逻辑 ==========
async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # 自动每日清空：清空数据文件并重置 last_msg_id
    if not is_manual and need_auto_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        reset_last_id()
        print("今日首次自动运行，已清空数据文件并重置消息ID")

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        # 1. 读取本地数据
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        is_first_run = (len(local_data) == 0)
        print(f"本地数据: {len(local_data)} 期，是否首次运行: {is_first_run}")

        # 2. 加载上次处理的消息ID
        last_id = load_last_id()
        print(f"上次处理的最大消息ID: {last_id}")

        # 3. 拉取新消息中的有效开奖
        all_valid, max_new_id = await fetch_messages_since(client, last_id)
        print(f"本次拉取到 {len(all_valid)} 条新有效开奖")

        if max_new_id:
            print(f"最新消息ID: {max_new_id}")

        if not all_valid:
            print("无新增有效开奖，退出")
            return

        # 4. 候选池：取最新 CANDIDATE_POOL_SIZE 条（若不足则全取）
        top_n = all_valid[:CANDIDATE_POOL_SIZE]
        print(f"候选池长度: {len(top_n)}，期号: {[get_period(m) for m in top_n]}")

        # 5. 选取新数据
        if is_first_run:
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(top_n))
            selected = top_n[:take]
            print(f"首次运行，取最新 {take} 期")
        else:
            candidates = [msg for msg in top_n if get_period(msg) not in local_periods]
            print(f"过滤本地后剩余候选: {len(candidates)} 条")
            if not candidates:
                print("候选池中无新期号，退出")
                # 仍然更新 last_id 以避免下次重复拉取
                if max_new_id:
                    save_last_id(max_new_id)
                return
            take = random.randint(1, MAX_TAKE)
            take = min(take, len(candidates))
            selected = random.sample(candidates, take)
            print(f"后续运行，随机抽取 {take} 期")

        if len(selected) > MAX_TAKE:
            raise RuntimeError(f"选取数量异常: {len(selected)} > {MAX_TAKE}")

        selected_periods = [get_period(m) for m in selected]
        print(f"本次选中期号: {selected_periods}")

        # 6. 合并、去重、排序、保留最近 MAX_KEEP 期
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

        # 7. 更新 last_msg_id（无论是否选取了新期号，都要记录已处理的最大ID）
        if max_new_id:
            save_last_id(max_new_id)
            print(f"已更新 last_msg_id 至 {max_new_id}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
