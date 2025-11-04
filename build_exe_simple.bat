@echo off
echo Building DennyAutoTools.exe...
echo.

REM Set Python path
set "PYTHON_EXE=D:\HusbandProgram\python\python.exe"

REM Check Python
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found at %PYTHON_EXE%
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

REM Install dependencies
echo Installing dependencies...
"%PYTHON_EXE%" -m pip install PySide6 pyinstaller requests urllib3
echo.

REM Clean old files
echo Cleaning old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del "*.spec"
if exist "test_download.py" del "test_download.py"
if exist "test_download.json" del "test_download.json"
if exist "demo.html" del "demo.html"

REM Build exe
echo Building executable...
"%PYTHON_EXE%" -m PyInstaller --onefile --windowed --name=DennyAutoTools --collect-all=PySide6 --hidden-import=requests --hidden-import=urllib3 --hidden-import=urllib3.util.retry main.py

REM Check result
if exist "dist\DennyAutoTools.exe" (
    echo.
    echo SUCCESS! Generated: dist\DennyAutoTools.exe
    echo.
    dir "dist\DennyAutoTools.exe"
    echo.
    set /p choice="Run the exe now? (y/n): "
    if /i "%choice%"=="y" (
        start "" "dist\DennyAutoTools.exe"
    )
) else (
    echo.
    echo ERROR: Build failed!
)

pause
