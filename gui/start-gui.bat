@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "node_modules\" (
  echo [game-ai-foundry] First run: npm install ...
  call npm install
  if errorlevel 1 exit /b 1
)

if defined GAMEFACTORY_ROOT (
  echo [game-ai-foundry] GAMEFACTORY_ROOT=%GAMEFACTORY_ROOT%
) else (
  for %%I in ("%~dp0..") do set "GAMEFACTORY_ROOT=%%~fI"
  set "GAMEFACTORY_ROOT=%GAMEFACTORY_ROOT%"
  echo [game-ai-foundry] GAMEFACTORY_ROOT=%GAMEFACTORY_ROOT%
)

echo [game-ai-foundry] Starting GUI (Vite + Electron) ...
echo [game-ai-foundry] If the window is blank, close it and run this bat again.
call npm run dev

endlocal
