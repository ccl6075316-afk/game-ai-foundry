@echo off
setlocal
REM Repo-local launcher: never use Windows Store python stubs.
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "ROOT_LAUNCHER=%ROOT%gamefactory.py"

if not exist "%VENV_PY%" (
  echo [gamefactory] .venv missing. Bootstrapping with setup ensure-python ...
  where py >nul 2>&1
  if %ERRORLEVEL%==0 (
    py -3 "%ROOT%cli\gamefactory.py" setup ensure-python
  ) else (
    REM Fall back to whatever python is on PATH; may fail on Store stubs.
    python "%ROOT%cli\gamefactory.py" setup ensure-python
  )
  if not exist "%VENV_PY%" (
    echo [gamefactory] Failed to create .venv. Install Python 3.11+ from python.org,
    echo then run:  py -3 cli\gamefactory.py setup ensure-python --json
    exit /b 1
  )
)

"%VENV_PY%" "%ROOT_LAUNCHER%" %*
exit /b %ERRORLEVEL%
