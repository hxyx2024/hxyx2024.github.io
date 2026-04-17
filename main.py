name: Lottery Fetcher

on:
  schedule:
    - cron: '0 10 * * *'   # UTC 10:00 = 北京时间 18:00
  workflow_dispatch:

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install telethon
      - name: Run script
        env:
          API_ID: ${{ secrets.API_ID }}
          API_HASH: ${{ secrets.API_HASH }}
        run: python main.py
