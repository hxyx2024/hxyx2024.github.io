from telethon import TelegramClient
import asyncio

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

async def main():
    async with TelegramClient("session", API_ID, API_HASH) as client:
        # 频道 @douapi
        msg = await client.get_messages("douapi", limit=1)
        if msg:
            with open("latest.txt", "w", encoding="utf-8") as f:
                f.write(msg[0].text)
            print("✅ 成功获取最新消息")

asyncio.run(main())
