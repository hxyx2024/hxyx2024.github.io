# 必用版：Windows 100% 弹出登录
from telethon import TelegramClient
import asyncio
import sys

API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

async def main():
    print("正在启动登录……")
    client = TelegramClient("session", API_ID, API_HASH)
    await client.start()
    print("=" * 50)
    print("✅ 登录成功！")
    print("✅ session.session 已生成！")
    print("=" * 50)
    await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("错误：", e)
        input("按回车退出")
