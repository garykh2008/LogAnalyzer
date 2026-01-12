@echo off
echo Installing dependencies for Log Analyzer (Qt version)...

python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo Error updating pip. Please ensure python is installed and in your PATH.
    pause
    exit /b %errorlevel%
)

echo Installing PySide6...
python -m pip install PySide6
if %errorlevel% neq 0 (
    echo Error installing PySide6.
    pause
    exit /b %errorlevel%
)

echo.
echo Dependencies installed successfully!
echo You can now run the application using: python -m qt_app.main
pause
