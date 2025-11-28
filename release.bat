@echo off
setlocal EnableDelayedExpansion

:: --- 設定區 ---
set "PYTHON_FILE=loganalyzer.py"
set "DOC_SCRIPT=build_docs.py"
set "DOC_DIR=Doc"
set "DOC_FILENAME=Log_Analyzer_v1.0_Docs_EN.html"
set "LINUX_PACKAGER=_linux_packager.py"
set "VERSION_SCRIPT=get_ver.py"

:: 輸出目錄設定
set "REL_ROOT=release"
set "REL_WIN=%REL_ROOT%\windows"

echo ========================================================
echo      Log Analyzer Release Automation Script
echo ========================================================

:: 0. 前置環境檢查與套件安裝
echo [0/5] Checking prerequisites...

python --version >nul 2>&1
if %errorlevel% neq 0 (
	echo [Error] Python is not installed or not found in PATH.
	pause
	exit /b 1
)

echo       Installing/Updating required packages...
pip install pyinstaller markdown
if %errorlevel% neq 0 (
	echo [Error] Failed to install dependencies.
	pause
	exit /b 1
)

:: 1. 檢查必要檔案
if not exist "%PYTHON_FILE%" (
	echo [Error] Could not find %PYTHON_FILE%
	pause
	exit /b 1
)
if not exist "%LINUX_PACKAGER%" (
	echo [Error] Could not find %LINUX_PACKAGER%. Please save it first.
	pause
	exit /b 1
)
if not exist "%VERSION_SCRIPT%" (
	echo [Error] Could not find %VERSION_SCRIPT%. Please save it first.
	pause
	exit /b 1
)

:: 2. 自動提取版本號 (僅用於 Windows 檔名命名，Linux 由 Python 腳本自行處理)
echo [1/5] Extracting version info...

:: [UPDATED] 直接呼叫已存在的 get_ver.py
for /f "delims=" %%i in ('python "%VERSION_SCRIPT%"') do set VERSION=%%i

if "%VERSION%"=="Unknown" (
	echo [Error] Could not detect version from self.VERSION using %VERSION_SCRIPT%
	pause
	exit /b 1
)

echo       Target Version: %VERSION%

:: 3. 生成文件
echo [2/5] Building documentation...
if exist "%DOC_SCRIPT%" (
	python "%DOC_SCRIPT%"
	if not exist "%DOC_DIR%" mkdir "%DOC_DIR%"
	if exist "%DOC_FILENAME%" (
		move /Y "%DOC_FILENAME%" "%DOC_DIR%\" >nul
		echo       Moved documentation to %DOC_DIR% folder.
	)
)

:: 4. Windows 打包 (PyInstaller)
echo [3/5] Building Windows Executable...

if not exist "%REL_WIN%" mkdir "%REL_WIN%"

:: [FIX] 使用絕對路徑指定來源資料夾，避免因 specpath=build 導致相對路徑錯誤
set "ABS_DOC_SRC=%~dp0%DOC_DIR%"

pyinstaller --noconsole --onefile --clean ^
	--distpath "%REL_WIN%" ^
	--workpath "build" ^
	--specpath "build" ^
	--add-data "%ABS_DOC_SRC%;%DOC_DIR%" ^
	--name "LogAnalyzer_%VERSION%" ^
	"%PYTHON_FILE%"

if %errorlevel% neq 0 (
	echo [Error] PyInstaller failed.
	pause
	exit /b 1
)

:: 5. Linux 打包 (呼叫 Python 腳本)
echo [4/5] Packaging for Linux...

python "%LINUX_PACKAGER%"

if %errorlevel% neq 0 (
	echo [Error] Linux packaging failed.
	pause
	exit /b 1
)

echo.
echo ========================================================
echo [5/5] All Tasks Completed!
echo ========================================================
echo.
echo Windows Release: %REL_WIN%\LogAnalyzer_%VERSION%.exe
echo Linux Release:   Check release\linux folder
echo.
pause