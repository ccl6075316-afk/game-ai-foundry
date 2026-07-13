@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo [release] Preparing embedded Python ...
python scripts\prepare_embedded_python.py --output gui\runtime\python --with-rembg
if errorlevel 1 exit /b 1

echo [release] Building GUI ...
cd gui
if not exist node_modules\ call npm install
call npm run build:app
if errorlevel 1 exit /b 1

echo [release] Done. Artifacts in gui\release\
endlocal
