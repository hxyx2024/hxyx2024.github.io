from telethon import TelegramClient
import asyncio
import socks

# 你的信息
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

# --------------------------
# V2Ray 通用 3 组端口 挨个试
# --------------------------
# 试试这 3 个，哪个能用就是哪个！

# 1. 最常见 V2Ray
proxy = (socks.SOCKS5, "127.0.0.1", 10808)

# 2. 如果上面超时，换成这个
# proxy = (socks.SOCKS5, "127.0.0.1", 20808)

# 3. 最后换这个
# proxy = (socks.HTTP, "127.0.0.1", 10809)

async def main():
    print("🔗 正在连接 Telegram...")
    client = TelegramClient(
        "session",
        API_ID,
        API_HASH,
        proxy=proxy,
        timeout=120
    )

    try:
        await client.start()
        print("\n✅ 登录成功！session.session 已生成！")
    except Exception as e:
        print("\n❌ 错误：", e)
        print("💡 请换上面的 proxy 端口再试！")

asyncio.run(main())
input("按回车退出")
