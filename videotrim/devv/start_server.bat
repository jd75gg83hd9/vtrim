@echo off
REM set current working directory to directory of this BAT, which is required by start_server.py
cd %~dp0
@echo on

internal\python\python.exe internal\start_server.py
pause