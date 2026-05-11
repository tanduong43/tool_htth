@echo off
chcp 65001 >nul
title Khởi động AutoGame

echo Kiem tra moi truong Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Loi] Chua cai dat Python. Vui long cai Python va thu lai!
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Tao moi truong ao .venv...
    python -m venv .venv
)

echo Kich hoat moi truong ao va cai dat thu vien...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo Khoi dong AutoGame Dashboard...
:: Su dung truc tiep python.exe trong .venv de tranh loi lay nham python he thong
start "" ".venv\Scripts\python.exe" AutoGame.py
exit
