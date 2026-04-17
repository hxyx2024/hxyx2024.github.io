from telethon import TelegramClient
import asyncio
import re
import random
import os
from datetime import datetime, timezone, timedelta
import traceback

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "lottery_data_api.html"
MAX_KEEP = 60
BEIJING_TZ = timezone(timedelta(hours=8))
FETCHED_FILE = ".fetched_periods.txt"
CLEAN_FLAG_FILE = ".last_clean_date"
AUTO_STOP_FILE = ".auto_stop_today"

PAGE_LIMIT = 100          # 仅用于兼容，实际使用 iter_messages 不分页
MAX_RETRIES = 3
RETRY_DELAY = 5
RANDOM_MIN = 1
RANDOM_MAX = 3

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

async def fetch_messages_with_retry(client, limit):
    # 此函数不再使用，保留仅为兼容
    pass

async def get_all_valid_messages(client):
    """使用 iter_messages 自动分页拉取所有消息，提取有效开奖结果"""
    result = {}
    count = 0
    print("开始拉取所有消息...")
    async for msg in client.iter_messages(CHANNEL, limit=None):
        if msg.text and "新澳门六合彩第" in msg.text:
            txt = msg.text.strip()
            if is_complete_lottery(txt):
                p = get_period(txt)
                if p not in result:
                    result[p] = txt
                    count += 1
                    if count % 50 == 0:
                        print(f"已拉取 {count} 期有效数据...")
        # 避免限流，适当延时
        await asyncio.sleep(0.02)
    print(f"总共拉取 {len(result)} 期有效数据")
    return result

def load_fetched_periods():
    if not os.path.exists(FETCHED_FILE):
        return set()
    with open(FETCHED_FILE, 'r') as f:
        return {int(line.strip()) for line in f if line.strip()}

def save_fetched_periods(periods):
    with open(FETCHED_FILE, 'w') as f:
        for p in sorted(periods):
            f.write(f"{p}\n")

def get_local_data():
    if not os.path.exists(OUT_FILE):
        return []
    with open(OUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return []
    data = []
    for block in content.split('\n\n'):
        if block and is_complete_lottery(block):
            data.append(block)
    return data

def need_clean_today():
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    if os.path.exists(CLEAN_FLAG_FILE):
        with open(CLEAN_FLAG_FILE, 'r') as f:
            if f.read().strip() == today:
                return False
    with open(CLEAN_FLAG_FILE, 'w') as f:
        f.write(today)
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

def is_auto_time():
    """判断当前时间是否在自动触发时段（北京时间18:00-21:20）"""
    now = datetime.now(BEIJING_TZ)
    hour = now.hour
    minute = now.minute
    if hour < 18 or hour > 21:
        return False
    if hour == 21 and minute >= 20:
        return False
    return True

async def main():
    is_manual = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    print(f"手动: {is_manual}")

    # 自动触发时段检查
    if not is_manual and not is_auto_time():
        print("不在自动触发时段 (18:00-21:20 北京时间)，退出")
        return

    # 每日首次运行清空数据（无论手动还是自动）
    if need_clean_today():
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        if os.path.exists(FETCHED_FILE):
            os.remove(FETCHED_FILE)
        clear_auto_stop()
        print("每日首次运行，已清空数据及已采集记录")

    # 自动触发检查停止标志
    if not is_manual and is_auto_stopped_today():
        print("自动触发已停止（今日无新数据）")
        return

    client = None
    try:
        client = TelegramClient("session", API_ID, API_HASH)
        await client.start()

        # 获取频道所有有效开奖结果
        all_periods_dict = await get_all_valid_messages(client)
        all_periods = set(all_periods_dict.keys())
        print(f"频道共 {len(all_periods)} 期有效数据")

        # 加载已采集期号
        fetched = load_fetched_periods()
        print(f"已采集 {len(fetched)} 期")

        # 未采集列表，按期号降序排序
        unfetched = sorted(all_periods - fetched, reverse=True)
        if not unfetched:
            print("无新数据")
            if not is_manual:
                set_auto_stop()
            return

        # 随机取1-3条（最大的前N条）
        take = random.randint(RANDOM_MIN, RANDOM_MAX)
        new_periods = unfetched[:take]
        print(f"本次采集 {len(new_periods)} 期: {new_periods}")

        # 读取本地现有数据
        old_data = get_local_data()
        old_periods = {get_period(x) for x in old_data}

        # 合并新数据
        all_data = old_data[:]
        for p in new_periods:
            txt = all_periods_dict[p]
            if p not in old_periods:
                all_data.append(txt)

        # 按期号升序排序，保留最多MAX_KEEP条
        all_data.sort(key=get_period)
        if len(all_data) > MAX_KEEP:
            all_data = all_data[-MAX_KEEP:]

        # 写入文件
        with open(OUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(all_data) + "\n")

        # 更新已采集集合
        fetched.update(new_periods)
        save_fetched_periods(fetched)

        print(f"完成，总期数 {len(all_data)}，新增 {len(new_periods)} 期，新增期号: {new_periods}")

    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()
    finally:
        if client:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
