@echo off
chcp 65001 >nul
title SIMMOON — Telegram Bot 🤖
cd /d "%~dp0Simmoon_arc"

echo.
echo  ════════════════════════════════════════
echo   🤖 SIMMOON Telegram Bot — @Jeremi_Hermes_bot
echo  ════════════════════════════════════════
echo.
echo  Iniciando bot...
echo  Presiona Ctrl+C para detener.
echo.

python telegram_bot.py

echo.
echo  Bot detenido.
pause
