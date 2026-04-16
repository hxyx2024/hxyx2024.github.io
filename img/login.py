from telethon import TelegramClient
import asyncio

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

async def main():
    client = TelegramClient(
        "session",
        API_ID,
        API_HASH,
        proxy=None  # 让它自动用你电脑全局代理
    )
    await client.start()
    print("✅ 登录成功！session.session 已生成")

asyncio.run(main())
input("按回车退出")
