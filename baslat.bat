@echo off
chcp 65001 > nul
title KPSS Atama Takip Sistemi

echo ========================================================
echo  KPSS Atama ve Personel Alim Takip Sistemi Baslatiliyor
echo ========================================================

if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe run.py
) else (
    python run.py
)

pause
