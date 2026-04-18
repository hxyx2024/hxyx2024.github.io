import os
import asyncio
import json
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
OUT_FILE = "ga_gb.txt"
STATE_FILE = "ga_gb_state.json"   # 记录已处理的消息ID

BEIJING_TZ = timezone(timedelta(hours=8))

def is_ga_gb_message(text):
    """判断消息是否为 G·A 或 G·B 格式"""
    lines = text.strip().split('\n')
    if not lines:
        return False
    first_line = lines[0].strip()
    return first_line in ("G · A", "G · B")

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
        # 拉取最新1条消息
        async for msg in client.iter_messages(CHANNEL, limit=1):
            if not msg.text:
                print("最新消息无文本内容")
                return
            txt = msg.text.strip()
            msg_id = msg.id

            last_id = load_last_id()
            if msg_id == last_id:
                print(f"消息ID {msg_id} 已处理过，跳过")
                return

            if is_ga_gb_message(txt):
                # 覆盖写入
                with open(OUT_FILE, 'w', encoding='utf-8') as f:
                    f.write(txt + "\n")
                save_last_id(msg_id)
                print(f"✅ 写入 {OUT_FILE}，消息ID: {msg_id}")
            else:
                print("最新消息不是 G·A/G·B 格式，不做操作")
            return  # 只处理一条，退出
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
