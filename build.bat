@echo off
chcp 65001 >nul
title Build AutoGame.exe

echo Kiem tra moi truong...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install pyinstaller pywin32 pynput pydirectinput

echo Dang build file thuc thi AutoGame.exe...
pyinstaller AutoGame.spec --clean -y

echo Hoan thanh! File EXE nam trong thu muc 'dist'.
pause
