@echo off
setlocal

:: ==========================================
::      Rust Extension Update Script
:: ==========================================

:: 設定 Rust 專案目錄 (根據您的錯誤訊息，資料夾名稱為 rust_extention)
set "RUST_DIR=rust_extention"

:: 設定 Python 執行檔 (如果您使用 PyPy，請改為: set "PYTHON_CMD=pypy")
set "PYTHON_CMD=python"

:: 設定安裝指令 (如果您使用 PyPy，請將下行改為: set "PIP_CMD=pypy -m pip")
set "PIP_CMD=pip"

echo [Update] Entering %RUST_DIR%...
cd %RUST_DIR%
if %errorlevel% neq 0 (
    echo [Error] Directory %RUST_DIR% not found!
    pause
    exit /b 1
)

echo [Update] Setting build environment variables...
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

echo [Update] Building Rust extension (Release mode)...
maturin build --release
if %errorlevel% neq 0 (
    echo [Error] Maturin build failed!
    cd ..
    pause
    exit /b 1
)

echo [Update] Installing generated wheel...
cd ..
for %%f in (%RUST_DIR%\target\wheels\*.whl) do (
    echo Found wheel: %%f
    %PIP_CMD% install "%%f" --force-reinstall
)

echo.
echo [Success] Rust extension updated successfully!
pause