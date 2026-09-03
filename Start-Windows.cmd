@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Setup-Windows.cmd first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "app.py"
