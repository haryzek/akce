@echo off
REM ============================================================
REM  Scraper akci - spousteni na dvojklik.
REM  Otevre GUI: vyber typ akce + rozmezi datumu a klikni Spustit.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Scraper akci

REM --- najdi Python (nejdriv launcher "py", pak "python") ---
where py >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=py
) else (
    set PYCMD=python
)

REM --- pri prvnim spusteni doinstaluj zavislosti (tise) ---
%PYCMD% -c "import requests, bs4" >nul 2>nul
if not %errorlevel%==0 (
    echo   Prvni spusteni: instaluji potrebne knihovny...
    %PYCMD% -m pip install -r requirements.txt
    echo.
)

REM --- spust GUI (tkinter je soucast Pythonu) ---
%PYCMD% gui.py
