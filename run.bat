@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  py -3 -m venv .venv || goto :err
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install torch --index-url https://download.pytorch.org/whl/cpu || goto :err
  pip install -r requirements.txt || goto :err
) else (
  call .venv\Scripts\activate.bat
)
python main.py
goto :eof
:err
echo Install failed. See README.md
pause
