@echo off
setlocal
set "REVIEW=%~dp0"
for %%G in ("%REVIEW%..\..\..\..\projects\fishing-2d\game") do set "GAME=%%~fG"
if not defined GF_GODOT set "GF_GODOT=%USERPROFILE%\.gamefactory\toolchain\godot\Godot_v4.7.1-stable_mono_win64\Godot_v4.7.1-stable_mono_win64.exe"
if not exist "%GF_GODOT%" (
    echo Set GF_GODOT to the path of your Godot 4.7.1 .NET executable.
    exit /b 1
)
if not exist "%GAME%\project.godot" (
    echo Pull the fishing-2d checkout under projects\fishing-2d first.
    exit /b 1
)
set "DOTNET=dotnet"
if exist "%USERPROFILE%\.gamefactory\toolchain\dotnet\dotnet.exe" (
    set "DOTNET_ROOT=%USERPROFILE%\.gamefactory\toolchain\dotnet"
    set "DOTNET=%USERPROFILE%\.gamefactory\toolchain\dotnet\dotnet.exe"
)
"%DOTNET%" build "%GAME%\GameFactoryDemo.csproj" --nologo -v:q
if errorlevel 1 exit /b 1
"%GF_GODOT%" --headless --path "%GAME%" --editor --import
if errorlevel 1 exit /b 1
start "Aquascape collection review" "%GF_GODOT%" --path "%GAME%" --rendering-method gl_compatibility --script "%REVIEW%review.gd" -- "%REVIEW%layouts.json"
