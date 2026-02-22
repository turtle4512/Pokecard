@echo off
chcp 65001 >nul
title PokeCard Web Server
echo ========================================
echo   PokeCard Web Server Starting...
echo   http://localhost:5000
echo ========================================
echo.
cd /d "%~dp0"
python -X utf8 run_web.py
pause
