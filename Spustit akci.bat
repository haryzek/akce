@echo off
chcp 65001 >nul
title Akce - lokalni server
cd /d "%~dp0"

echo.
echo   Startuji appku Akce...
echo   Az domerguju, otevre se prohlizec.
echo.
echo   TOTO OKNO NECHEJ OTEVRENE - zavrenim appku vypnes.
echo.

rem otevre prohlizec (server nabehne behem chvilky, browser si pocka)
start "" http://localhost:8000/

rem spusti vestaveny Python server ve slozce appky (drzi bezet dokud okno nezavres)
python -m http.server 8000
