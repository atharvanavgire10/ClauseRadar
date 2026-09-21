@echo off
REM ClauseRadar local dev bootstrap (Windows)
REM Usage: scripts\dev_setup.bat
setlocal
copy /Y .env.example .env >nul 2>&1
py -m pip install --upgrade pip
py -m pip install -r backend\requirements.txt
py backend\manage.py migrate
echo Done. Run: py backend\manage.py runserver  (backend)  and  npm --prefix frontend install ^& npm --prefix frontend run dev  (frontend)
