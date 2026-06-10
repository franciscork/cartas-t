@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\Program Files\PowerShell\7\Simmoon_arc"
"C:\Users\docus\AppData\Local\Programs\Python\Python311\python.exe" -X utf8 juego_simmoon.py
