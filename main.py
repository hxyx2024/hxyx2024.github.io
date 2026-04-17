import os
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

MAX_TAKE = 4               # 固定取 4 条
INIT_FETCH_LIMIT = 4       # 每次拉取最近 4 条消息

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
    """检查今日是否已经清空过（仅用于自动运行）"""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w') as f:
        f.write(today)
    return True

def is_auto_time():
    """自动运行时段：18:00–21:20 北京时间"""
    now = datetime.now(BEIJING_TZ)
    hour, minute = now.hour, now.minute
    if hour < 18 or hour > 21:
        return False
    if hour == 21 and minute >= 20:
        return False
    return True

async def fetch_recent_messages(client, limit):
    """
    拉取最近 limit 条消息，返回有效开奖文本列表（按消息ID升序，即时间从旧到新）
    """
    valid = []  # 每个元素为 (msg_id, text)
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if msg.text and "新澳门六合彩第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                valid.append((msg.id, txt))
    # 按消息ID升序排列（越早的越前）
    valid.sort(key=lambda x: x[0])
    return [txt for _, txt in valid]

# ========== 主逻辑 ==========
async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"触发方式: {'手动' if is_manual else '自动'}")

    # 自动运行：检查时段
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # 自动运行：每日首次清空数据文件
    if not is_manual and need_auto_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        print("今日首次自动运行，已清空数据文件")

    client = await TelegramClient("session", API_ID, API_HASH).start()

    try:
        # 1. 读取本地数据
        local_data = get_local_data()
        local_periods = {get_period(b) for b in local_data}
        print(f"本地数据: {len(local_data)} 期")

        # 2. 拉取最近 4 条消息中的有效开奖
        all_valid = await fetch_recent_messages(client, INIT_FETCH_LIMIT)
        print(f"从最近 {INIT_FETCH_LIMIT} 条消息中提取到 {len(all_valid)} 条有效开奖")

        if not all_valid:
            print("未拉取到任何有效开奖，退出")
            return

        # 3. 过滤出本地没有的期号（保持原有顺序，旧→新）
        new_periods = []
        for txt in all_valid:
            p = get_period(txt)
            if p and p not in local_periods:
                new_periods.append(txt)
        print(f"新期号数量: {len(new_periods)}")

        if not new_periods:
            print("无新期号，退出")
            return

        # 4. 固定取 4 条（最新的 4 条，即列表末尾的 4 条）
        take = min(MAX_TAKE, len(new_periods))
        selected = new_periods[-take:]   # 取最新的 take 条
        print(f"本次选取 {take} 期，期号: {[get_period(m) for m in selected]}")

        # 5. 合并、去重、排序、保留最近 MAX_KEEP 期
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

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
