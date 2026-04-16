from telethon import TelegramClient
import asyncio
import socks

# 你的信息
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

# ✅ 国内必须加这个！你是 10808 端口
proxy = (socks.SOCKS5, "127.0.0.1", 10808)

async def main():
    print("✅ 已开启V2Ray代理，正在登录...")

    client = TelegramClient(
        "session",
        API_ID,
        API_HASH,
        proxy=proxy,  # 代理已写好
        timeout=120
    )

    await client.start()
    print("\n🎉 登录成功！")
    print("🎉 session.session 已生成！")

# 固定不会闪退
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("错误：", e)
    input("按回车退出")
