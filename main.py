# 仅清空文件，不联网、不采集、不抓数据
if __name__ == "__main__":
    # 要清空的文件
    file_path = "lottery_data.html"
    
    # 直接清空内容
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("")
    
    print("✅ 清空完成，未拉取任何数据")
