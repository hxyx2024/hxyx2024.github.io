import os
import asyncio
import json
import re
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"

OUTPUT_FILE = "antdata.html"
STATE_FILE = "antdata_state.json"

PERIOD_RE = re.compile(r"新澳门六合彩第[:\s]*(\d{7})期")

def extract_period(text):
    m = PERIOD_RE.search(text)
    return int(m.group(1)) if m else 0

def is_valid_number_line(line):
    """检查一行是否为恰好7个数字（1-49），且只包含数字和空格"""
    line = line.strip()
    if not line:
        return False
    if re.search(r'[^0-9\s]', line):
        return False
    nums = re.findall(r'\d+', line)
    if len(nums) != 7:
        return False
    for n in nums:
        num = int(n)
        if num < 1 or num > 49:
            return False
    return True

def load_last_id():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_msg_id', 0)
        except:
            return 0
    return 0

def save_last_id(msg_id):
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_msg_id': msg_id}, f)

async def main():
    client = await TelegramClient("session_ga", API_ID, API_HASH).start()
    try:
        async for msg in client.iter_messages(CHANNEL, limit=1):
            if not msg.text:
                print("最新消息无文本内容")
                return
            txt = msg.text.strip()
            msg_id = msg.id

            period = extract_period(txt)
            if period == 0:
                print("消息不包含期号，跳过")
                return

            lines = txt.split('\n')
            numbers = None
            for line in lines:
                if is_valid_number_line(line):
                    nums = [int(n) for n in re.findall(r'\d+', line)]
                    if len(nums) == 7:
                        numbers = nums
                        break
            if numbers is None:
                print("未找到7个数字的行，跳过")
                return

            last_id = load_last_id()
            if msg_id == last_id:
                print(f"消息ID {msg_id} 已处理过，跳过")
                return

            te = numbers[-1]

            # 读取现有特码列表
            existing = []
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    existing = [line.strip() for line in f if line.strip()]

            # 插入新特码到开头，保留最新60期
            existing.insert(0, str(te))
            existing = existing[:60]

            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                for te_line in existing:
                    f.write(te_line + "\n")
            save_last_id(msg_id)
            print(f"✅ 已更新 {OUTPUT_FILE}，当前共 {len(existing)} 个特码，最新特码: {te}")

            return
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
