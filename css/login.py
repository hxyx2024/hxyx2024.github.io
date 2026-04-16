from telethon import TelegramClient
import asyncio
import os

# 你的 API
API_ID = 36088286
API_HASH = "7b78971ae31f48f666c2148c761cca41"

# 强制指定 session 路径，解决权限问题
SESSION_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "my_session")

async def main():
    print("正在启动登录（已修复权限问题）……")
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()
    print("✅ 登录成功！")
    print("✅ my_session.session 已生成在桌面")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("错误：", e)
    input("按回车退出")
