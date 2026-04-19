import os
import asyncio
import re
from telethon import TelegramClient
from collections import defaultdict

# 环境变量
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
CHANNEL = "douapi"
FETCH_LIMIT = 200          # 拉取最近200条消息，足够覆盖60+30期
OUTPUT_FILE = "gab_summary.html"

# 正则提取期号（支持多种格式）
PERIOD_RE = re.compile(r"新澳门(?:六合彩)?第[:\s]*(\d{7})期")

def extract_period(text):
    m = PERIOD_RE.search(text)
    return int(m.group(1)) if m else 0

def is_complete_lottery(text):
    """判断是否为完整开奖消息：至少4行，第二行有7个数字，第三行有生肖，第四行有颜色"""
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 4:
        return False
    # 第二行应包含7个数字
    nums = re.findall(r'\d+', lines[1])
    if len(nums) != 7:
        return False
    # 第三行应包含7个生肖汉字
    zodiacs = re.findall(r'[鼠牛虎兔龍蛇馬羊猴雞狗豬]', lines[2])
    if len(zodiacs) != 7:
        return False
    # 第四行应包含7个颜色符号
    colors = re.findall(r'[🟢🔴🔵]', lines[3])
    if len(colors) != 7:
        return False
    return True

def parse_numbers(text):
    """从消息的第二行提取7个数字"""
    lines = text.split('\n')
    if len(lines) < 2:
        return []
    nums = re.findall(r'\d+', lines[1])
    return [int(n) for n in nums[:7]]

async def fetch_lotteries(client, limit):
    """拉取最近limit条消息，返回列表[(period, numbers), ...] 按期号降序"""
    items = []
    async for msg in client.iter_messages(CHANNEL, limit=limit):
        if not msg.text:
            continue
        txt = msg.text.strip()
        if not is_complete_lottery(txt):
            continue
        period = extract_period(txt)
        if period == 0:
            continue
        numbers = parse_numbers(txt)
        if len(numbers) != 7:
            continue
        items.append((period, numbers))
    # 按期号降序排序
    items.sort(key=lambda x: x[0], reverse=True)
    return items

def format_period(period):
    """期号显示格式：实际期号+1，例如 2026109 -> 2026110"""
    return f"新澳彩第: {period+1}期"

def generate_html(lotteries):
    """
    lotteries: 列表 [(period, [n1..n7]), ...] 已按期号降序（最新在前）
    生成HTML内容（纯文本格式，放在<pre>中）
    """
    if not lotteries:
        return "<html><body><pre>暂无数据</pre></body></html>"
    
    # 最新60期（取前60）
    latest_60 = lotteries[:60]
    # 最新10期（取前10）
    latest_10 = lotteries[:10]
    # 最新30期（取前30）
    latest_30 = lotteries[:30]
    
    # 顶部期号：最新60期中的最新一期（即latest_60[0]）的期号+1
    top_period = latest_60[0][0] + 1 if latest_60 else 0
    top_line = f"新澳彩第: {top_period}期"
    
    lines = []
    lines.append(top_line)
    lines.append("GA")
    lines.append("")
    
    # GA 最新10期：每期一行，格式 "前6个数字（空格） 全部7个数字"
    for period, nums in latest_10:
        period_str = format_period(period)
        # 前6个数字
        first6 = " ".join(str(n) for n in nums[:6])
        all7 = " ".join(str(n) for n in nums)
        lines.append(f"{first6}  {all7}")
    lines.append("")
    
    # GA 最新60期：每期一行，只显示最后1个数字
    for period, nums in latest_60:
        period_str = format_period(period)
        lines.append(str(nums[-1]))
    lines.append("")
    lines.append("...................")
    lines.append("")
    
    # GB 最新30期：每期一行，全部7个数字
    for period, nums in latest_30:
        lines.append(" ".join(str(n) for n in nums))
    
    # 将所有行用换行符连接，放入<pre>标签
    content = "\n".join(lines)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>GA/GB 统计</title>
    <style>
        body {{ background: #121212; color: #eee; font-family: monospace; padding: 20px; }}
        pre {{ white-space: pre-wrap; font-size: 14px; }}
    </style>
</head>
<body>
<pre>
{content}
</pre>
</body>
</html>"""
    return html

async def main():
    client = await TelegramClient("session_gab", API_ID, API_HASH).start()
    try:
        lotteries = await fetch_lotteries(client, FETCH_LIMIT)
        if not lotteries:
            print("未拉取到任何有效开奖数据")
            return
        html = generate_html(lotteries)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ 已生成 {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
