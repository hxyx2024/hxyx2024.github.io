import os
import asyncio
import json
import re
from telethon import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"

# 输出文件
ANTDATA_OUT = "antdata.html"      # 新文件，存储完整消息（期号+GA/GB）
RULES_OUT = "default_rules.txt"   # 保持不变

# 状态文件
ANTDATA_STATE = "antdata_state.json"
RULES_STATE = "default_rules_state.json"

def is_antdata_message(text):
    """检查消息是否包含期号和 G·A/G·B 完整数据"""
    return "新澳门第:" in text and "G · A" in text and "G · B" in text

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
        # 获取最新一条消息（或可改为获取多条，但需求是最新一条）
        async for msg in client.iter_messages(CHANNEL, limit=1):
            if not msg.text:
                print("最新消息无文本内容")
                return
            txt = msg.text.strip()
            msg_id = msg.id

            # 优先检查是否是 antdata 完整消息
            if is_antdata_message(txt):
                last_id = load_last_id(ANTDATA_STATE)
                if msg_id == last_id:
                    print(f"antdata 消息ID {msg_id} 已处理过，跳过")
                else:
                    with open(ANTDATA_OUT, 'w', encoding='utf-8') as f:
                        f.write(txt + "\n")
                    save_last_id(ANTDATA_STATE, msg_id)
                    print(f"✅ 写入 {ANTDATA_OUT}，消息ID: {msg_id}")
                return

            # 否则检查是否是规则格式消息
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

            print("最新消息不是 antdata 格式也不是规则格式，不做操作")
            return
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
