from telethon import TelegramClient
import asyncio
import os

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

# 你要采集的频道：https://t.me/douapi
CHANNEL = "douapi"

async def main():
    client = TelegramClient("session", API_ID, API_HASH)
    try:
        await client.start()
        print("✅ 登录成功")

        # 获取最新1条消息
        msg = await client.get_messages(CHANNEL, limit=1)
        if msg:
            content = msg[0].text
            print("📩 最新消息：")
            print(content)

            # 保存到文件
            with open("data.txt", "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ 已保存到 data.txt")
        else:
            print("❌ 未获取到消息")
    except Exception as e:
        print("❌ 错误：", e)

asyncio.run(main())
