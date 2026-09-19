@echo off
setlocal
echo ==============================================
echo AI Fake Identity Document Screening - Setup
echo ==============================================
python --version
if errorlevel 1 (
  echo Python was not found. Install Python 3.13 and try again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
)
echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
echo Upgrading pip...
python -m pip install --upgrade pip
echo Installing dependencies...
pip install -r requirements.txt
echo Generating synthetic demo samples...
python make_samples.py
echo.
echo Setup complete.
echo Run the application with run.bat
pause
