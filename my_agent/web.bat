@echo off
cd /d "%~dp0"
echo Starting web server...
python -c "from my_agent.web.server import run; run()"
pause
