import os
import asyncio
import json
import re
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"

# 输出文件
GA_GB_OUT = "ga_gb.txt"
RULES_OUT = "default_rules.txt"

# 状态文件
GA_GB_STATE = "ga_gb_state.json"
RULES_STATE = "default_rules_state.json"

def is_ga_gb_message(text):
    lines = text.strip().split('\n')
    if not lines:
        return False
    first_line = lines[0].strip()
    return first_line in ("G · A", "G · B")

def is_rules_format(text):
    """检查消息是否全部由类似 '数字 数字' 的行组成（可含空行）"""
    lines = text.strip().split('\n')
    if not lines:
        return False
    for line in lines:
        line = line.strip()
        if line == "":
            continue
        if not re.match(r'^\d{1,2}\s+\d{1,2}$', line):
            return False
    return True

def load_last_id(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
                return data.get('last_msg_id', 0)
        except:
            return 0
    return 0

def save_last_id(state_file, msg_id):
    with open(state_file, 'w') as f:
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

            # 检查 G·A/G·B 格式
            if is_ga_gb_message(txt):
                last_id = load_last_id(GA_GB_STATE)
                if msg_id == last_id:
                    print(f"GA/GB 消息ID {msg_id} 已处理过，跳过")
                else:
                    with open(GA_GB_OUT, 'w', encoding='utf-8') as f:
                        f.write(txt + "\n")
                    save_last_id(GA_GB_STATE, msg_id)
                    print(f"✅ 写入 {GA_GB_OUT}，消息ID: {msg_id}")
                # 注意：一条消息不可能同时是两种格式，所以这里直接返回
                return

            # 检查规则格式
            if is_rules_format(txt):
                last_id = load_last_id(RULES_STATE)
                if msg_id == last_id:
                    print(f"规则消息ID {msg_id} 已处理过，跳过")
                else:
                    with open(RULES_OUT, 'w', encoding='utf-8') as f:
                        f.write(txt + "\n")
                    save_last_id(RULES_STATE, msg_id)
                    print(f"✅ 写入 {RULES_OUT}，消息ID: {msg_id}")
                return

            print("最新消息不是 GA/GB 也不是规则格式，不做操作")
            return
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
