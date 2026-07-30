@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo [release] Preparing embedded Python ...
python scripts\prepare_embedded_python.py --output gui\runtime\python --with-rembg
if errorlevel 1 exit /b 1

echo [release] Preparing embedded Pi ...
node scripts\prepare_embedded_pi.mjs --output gui\runtime\pi
if errorlevel 1 exit /b 1

echo [release] Building GUI ...
cd gui
call npm install
if errorlevel 1 exit /b 1
if "%PUBLISH%"=="1" (
  echo [release] Publishing to GitHub Releases ...
  call npm run build
  if errorlevel 1 exit /b 1
  call npx electron-builder --publish always
  if errorlevel 1 exit /b 1
) else (
  call npm run build:app
  if errorlevel 1 exit /b 1
  echo [release] Tip: set PUBLISH=1 and GH_TOKEN to upload auto-update metadata
)

echo [release] Done. Artifacts in gui\release\
endlocal
