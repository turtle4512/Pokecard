@echo off
chcp 65001 >nul
title PokeCard Telegram Bot
echo ========================================
echo   PokeCard Telegram Bot Starting...
echo   @pokeka_iibot
echo ========================================
echo.
cd /d "%~dp0"
python -X utf8 run_telegram.py
pause
