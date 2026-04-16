from telethon import TelegramClient
import asyncio
import socks

# 你的信息
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

# ✅ ✅ ✅ V2Ray 代理（必须写这里，系统代理无效）
proxy = (socks.SOCKS5, "127.0.0.1", 10808)

async def main():
    print("✅ 已启用 V2Ray 代理，正在登录...")

    client = TelegramClient(
        "session",
        API_ID,
        API_HASH,
        proxy=proxy,  # 代理写死在这里
        timeout=60
    )

    await client.start()
    print("")
    print("="*50)
    print("✅ 登录成功！session.session 已生成")
    print("="*50)

asyncio.run(main())
input("按回车退出")
