@echo off
cd /d D:\DS-N8N-CHAT
call .venv\Scripts\activate.bat
python -m news_digest.main >> logs\scheduler_stdout.log 2>&1
