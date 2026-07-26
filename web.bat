@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%
echo.
echo  ========================================
echo    BArt AI - Starting Web Server
echo  ========================================
echo.
echo  Open http://localhost:8080 in your browser
echo  Press Ctrl+C to stop the server
echo.
start "" http://localhost:8080
python main.py web
pause
