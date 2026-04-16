from telethon import TelegramClient, events
import asyncio
import os

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c21cca41d48741"
SESSION_FILE = "session.session"

# 这里改成你自己的频道用户名/链接/ID
CHANNEL_USERNAME = "你的频道用户名"

DATA_FILE = "lottery_data.txt"

async def main():
    if not os.path.exists(SESSION_FILE):
        print("未找到session文件")
        return

    client = TelegramClient(
        "session",
        API_ID,
        API_HASH
    )

    try:
        await client.start()
        print("登录成功")

        # 获取最新一条消息
        messages = await client.get_messages(CHANNEL_USERNAME, limit=1)
        if not messages:
            print("频道内暂无消息")
            return

        msg = messages[0]
        text = msg.text
        print("获取到内容：")
        print(text)

        # 保存到文件
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(text)

        print("已保存到", DATA_FILE)

    except Exception as e:
        print("错误:", e)

if __name__ == "__main__":
    asyncio.run(main())
