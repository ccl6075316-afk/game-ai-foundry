@echo off
setlocal
set "REVIEW=%~dp0"
for %%G in ("%REVIEW%..\..\..\..") do set "FOUNDRY=%%~fG"
set "GAME=%FOUNDRY%\projects\fishing-2d\game"
set "SCRATCH=%FOUNDRY%\work\surface-repair-20261124\review"
if not defined GF_GODOT set "GF_GODOT=%USERPROFILE%\.gamefactory\toolchain\godot\Godot_v4.7.1-stable_mono_win64\Godot_v4.7.1-stable_mono_win64.exe"
if not exist "%GF_GODOT%" (
    echo Set GF_GODOT to your Godot 4.7.1 .NET executable.
    exit /b 1
)
if not exist "%GAME%\project.godot" (
    echo Pull the fishing-2d checkout under projects\fishing-2d first.
    exit /b 1
)
if exist "%USERPROFILE%\.gamefactory\toolchain\dotnet\dotnet.exe" set "DOTNET_ROOT=%USERPROFILE%\.gamefactory\toolchain\dotnet"
if defined DOTNET_ROOT set "PATH=%DOTNET_ROOT%;%PATH%"
if not exist "%GAME%\.godot\mono\temp\bin\Debug\GameFactoryDemo.dll" (
    dotnet build "%GAME%\GameFactoryDemo.csproj" --nologo -v:q
    if errorlevel 1 exit /b 1
)
"%GF_GODOT%" --headless --editor --import --path "%GAME%"
if errorlevel 1 exit /b 1
if /I "%~1"=="--before" (
    py -3 "%REVIEW%prepare_baseline.py" "%SCRATCH%\baseline"
    if errorlevel 1 exit /b 1
    start "Aquascape material review" "%GF_GODOT%" --path "%GAME%" --rendering-method gl_compatibility --script "%REVIEW%inspector.gd" -- --baseline "%SCRATCH%\baseline"
    exit /b
)
start "Aquascape material review" "%GF_GODOT%" --path "%GAME%" --rendering-method gl_compatibility --script "%REVIEW%inspector.gd"
