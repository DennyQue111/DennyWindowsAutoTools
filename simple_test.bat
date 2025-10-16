@echo off
echo Testing Python environment...
echo.

REM Test Python path
if exist "D:\HusbandProgram\python\python.exe" (
    echo Found Python at: D:\HusbandProgram\python\python.exe
    "D:\HusbandProgram\python\python.exe" --version
    echo.
    
    echo Testing PySide6...
    "D:\HusbandProgram\python\python.exe" -c "import PySide6; print('PySide6 OK')"
    echo.
    
    echo Testing PyInstaller...
    "D:\HusbandProgram\python\python.exe" -c "import PyInstaller; print('PyInstaller OK')" 2>nul
    if %errorlevel% neq 0 (
        echo Installing PyInstaller...
        "D:\HusbandProgram\python\python.exe" -m pip install pyinstaller
    )
    echo.
    
    echo All tests completed!
    echo You can now run: build_exe_simple.bat
) else (
    echo ERROR: Python not found at D:\HusbandProgram\python\python.exe
    echo Please check your Python installation path
)

pause
