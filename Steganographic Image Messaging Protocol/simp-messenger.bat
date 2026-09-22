@echo off
cd /d "%~dp0"
python -m simp messenger
if errorlevel 1 pause
