@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python wechat_auto_reply.py
pause
