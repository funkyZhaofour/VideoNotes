@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
py -3.11 -c "import sys" >nul 2>nul
if not errorlevel 1 goto python311
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 goto python312
python -c "import sys; assert (3,11) <= sys.version_info[:2] < (3,13)" >nul 2>nul
if not errorlevel 1 goto pythonpath
echo Install Python 3.11 or 3.12 64-bit from https://www.python.org/downloads/windows/
echo Then run Setup-Windows.cmd again.
pause
exit /b 1
:python311
py -3.11 setup.py
goto finished
:python312
py -3.12 setup.py
goto finished
:pythonpath
python setup.py
:finished
if errorlevel 1 echo Setup failed. Please read the error above.
pause
