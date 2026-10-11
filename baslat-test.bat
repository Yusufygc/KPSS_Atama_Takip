@echo off
chcp 65001 > nul
title KPSS Atama Takip - TEST ORTAMI

echo ========================================================
echo  TEST ORTAMI (Telegram kapali, ayri test veritabani)
echo  Adres: http://127.0.0.1:8001
echo ========================================================

set PYEXE=python
if exist venv\Scripts\python.exe set PYEXE=venv\Scripts\python.exe

if not exist data\test\kpss_test.db (
    echo Test veritabani yok, ornek verilerle olusturuluyor...
    %PYEXE% scripts\seed_test_db.py
)

%PYEXE% run.py --test
pause
