@echo off
cd /d "%~dp0"
if exist .venv goto :run

set PYV=
for %%v in (3.12 3.11 3.10) do (
  if not defined PYV (
    py -%%v --version >nul 2>&1 && set PYV=%%v
  )
)
if not defined PYV (
  echo Python 3.10-3.12 was not found. Your newer Python ^(e.g. 3.14^) may not work with PyTorch/PySide6.
  echo Install Python 3.12 from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again.
  pause
  exit /b 1
)
echo Using Python %PYV%. Creating virtual environment...
py -%PYV% -m venv .venv || goto :err
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu || goto :err
pip install -r requirements.txt || goto :err
goto :start

:run
call .venv\Scripts\activate.bat
:start
python main.py
goto :eof

:err
echo Install failed. Delete the .venv folder and see README.md
pause
