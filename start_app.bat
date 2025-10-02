@echo off
cd /d "%~dp0"

REM 
if not exist venv\Scripts\pythonw.exe (
    echo [!] Sanal ortam oluşturuluyor ve bağımlılıklar yükleniyor. Lütfen bekleyin...
    python -m venv venv
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
)

REM 
venv\Scripts\pythonw.exe main.py
