@echo off
echo Starting dependency check for Log Analyzer...

set "PYTHON_CMD=python"

:: 1. Check for Python
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    :: Try 'py' launcher if 'python' fails
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py"
        goto :python_found
    )
    
    echo [X] Python not found. Please install Python 3.
    echo     Note: Ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

:python_found
echo [V] Python is already installed (using %PYTHON_CMD%).

:: 2. Update pip
echo [*] Updating pip...
%PYTHON_CMD% -m pip install --upgrade pip

:: 3. Install Python Dependencies
echo [*] Installing PySide6 and Maturin...
%PYTHON_CMD% -m pip install PySide6 maturin
if %errorlevel% neq 0 (
    echo [!] Warning: Some Python dependencies failed to install.
) else (
    echo [V] Python dependencies are ready.
)

:: 4. Check for Rust
cargo --version >nul 2>&1
if %errorlevel% neq 0 goto :rust_not_found

echo [V] Rust (cargo) is already installed.
goto :end_checks

:rust_not_found
echo [!] Warning: Rust (cargo) not found. You need Rust to build the extension.
echo     Please install from https://rustup.rs/

:end_checks
echo.
echo --- All checks completed! ---
pause
