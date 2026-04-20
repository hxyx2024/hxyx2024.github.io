name: Collect LaoAo and HK Lottery

on:
  schedule:
    - cron: '*/5 18-21 * * *'   # 北京时间 18:00-21:55 每5分钟一次（可根据需要调整）
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: pip install telethon

      - name: Restore Telegram session
        env:
          SESSION_BASE64: ${{ secrets.SESSION_BASE64 }}
        run: |
          if [ -n "$SESSION_BASE64" ]; then
            echo "$SESSION_BASE64" | base64 -d > session.session
          fi

      - name: Run lottery collection script
        env:
          API_ID: ${{ secrets.API_ID }}
          API_HASH: ${{ secrets.API_HASH }}
        run: python HKLAO__lottery.py

      - name: Commit and push changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add laoao_lottery_data.html hk_lottery_data.html .last_clean_date
          git diff --quiet && git diff --staged --quiet || git commit -m "Update LaoAo and HK lottery data [skip ci]"
          git pull --rebase origin main
          git push
