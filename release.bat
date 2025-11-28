@echo off
setlocal EnableDelayedExpansion

:: =================================================================
::      Log Analyzer Super Release Script
:: =================================================================
:: This script will:
:: 1. Update the version number in loganalyzer.py
:: 2. Build the docs, Windows exe, and Linux package
:: 3. Commit and tag the release in Git
:: =================================================================

:: --- 1. Version Check & Setup ---
if "%~1"=="" (
    echo [Error] No version number provided.
    echo Usage: %~nx0 vX.Y
    echo Example: %~nx0 v1.3
    exit /b 1
)
set "NEW_VER=%~1"
echo --- Preparing to release version: %NEW_VER% ---

:: --- 2. Get Current Version from get_ver.py ---
echo.
echo [Step 1/7] Reading current version...
for /f "delims=" %%i in ('python get_ver.py') do set "OLD_VER=%%i"
if "%OLD_VER%"=="Unknown" (
    echo [Error] Could not determine current version from get_ver.py. Aborting.
    exit /b 1
)
echo      Current version is %OLD_VER%. New version will be %NEW_VER%.

if /I "%OLD_VER%"=="%NEW_VER%" (
    echo [Warning] New version is the same as the current version.
    choice /C YN /M "Do you want to proceed with the build and commit anyway?"
    if errorlevel 2 exit /b 0
)

:: --- 3. Update Version in Python Script ---
echo.
echo [Step 2/7] Updating version in loganalyzer.py...
python _update_version.py %NEW_VER%
if %errorlevel% neq 0 (
    echo [Error] Failed to update version number using _update_version.py.
    exit /b 1
)
echo      Successfully updated loganalyzer.py to %NEW_VER%.

:: --- 4. Build Process ---
echo.
echo [Step 3/7] Installing dependencies...
pip install pyinstaller markdown tkinterdnd2 > nul
if %errorlevel% neq 0 (
	echo [Error] Failed to install dependencies.
	pause
	exit /b 1
)

echo.
echo [Step 4/7] Building...
:: Call the original build logic, but with the NEW version number
set "PYTHON_FILE=loganalyzer.py"
set "DOC_SCRIPT=build_docs.py"
set "DOC_DIR=Doc"
set "LINUX_PACKAGER=_linux_packager.py"
set "REL_WIN=release\windows"

echo      Finding tkinterdnd2 path...
for /f "delims=" %%i in ('python -c "import os, tkinterdnd2; print(os.path.dirname(tkinterdnd2.__file__))"') do set "TKINTERDND2_PATH=%%i"
if not defined TKINTERDND2_PATH ( echo [Error] tkinterdnd2 not found. && exit /b 1 )

echo      Building documentation...
python "%DOC_SCRIPT%"

echo      Building Windows Executable...
if not exist "%REL_WIN%" mkdir "%REL_WIN%"
set "ABS_DOC_SRC=%~dp0%DOC_DIR%"
pyinstaller --noconfirm --noconsole --onefile --clean --distpath "%REL_WIN%" --workpath "build" --specpath "build" --add-data "%ABS_DOC_SRC%;%DOC_DIR%" --add-data "!TKINTERDND2_PATH!;tkinterdnd2" --name "LogAnalyzer_%NEW_VER%" "%PYTHON_FILE%" > build/pyinstaller.log 2>&1
if %errorlevel% neq 0 (
	echo [Error] PyInstaller failed. Check build/pyinstaller.log
	exit /b 1
)

echo      Packaging for Linux...
python "%LINUX_PACKAGER%" > build/linux_packager.log 2>&1
if %errorlevel% neq 0 (
	echo [Error] Linux packaging failed. Check build/linux_packager.log
	exit /b 1
)

echo      Build complete.

:: --- 5. Git Operations ---
echo.
echo [Step 5/7] Staging files for commit...

:: Define old/new filenames
set "OLD_HTML_FILE=Doc\Log_Analyzer_%OLD_VER%_Docs_EN.html"
set "OLD_EXE_FILE=release\windows\LogAnalyzer_%OLD_VER%.exe"
set "OLD_TAR_FILE=release\linux\LogAnalyzer_%OLD_VER%_Linux.tar.gz"
set "NEW_HTML_FILE=Doc\Log_Analyzer_%NEW_VER%_Docs_EN.html"
set "NEW_EXE_FILE=release\windows\LogAnalyzer_%NEW_VER%.exe"
set "NEW_TAR_FILE=release\linux\LogAnalyzer_%NEW_VER%_Linux.tar.gz"

:: Remove old documentation file from Git index if it exists and filenames differ
if exist "%OLD_HTML_FILE%" (
    if /I "%OLD_HTML_FILE%" neq "%NEW_HTML_FILE%" (
        echo      Removing old doc file from Git: %OLD_HTML_FILE%
        git rm "%OLD_HTML_FILE%" > nul
    )
)

if exist "%OLD_EXE_FILE%" (
    if /I "%OLD_EXE_FILE%" neq "%NEW_EXE_FILE%" (
        echo      Removing old doc file from Git: %OLD_EXE_FILE%
        git rm "%OLD_EXE_FILE%" > nul
    )
)

if exist "%OLD_TAR_FILE%" (
    if /I "%OLD_TAR_FILE%" neq "%NEW_TAR_FILE%" (
        echo      Removing old doc file from Git: %OLD_TAR_FILE%
        git rm "%OLD_TAR_FILE%" > nul
    )
)

:: Add all new/modified files
echo      Adding new release files to Git...
git add loganalyzer.py "%NEW_HTML_FILE%" "%NEW_EXE_FILE%" "%NEW_TAR_FILE%"

:: --- 6. Commit ---
set "GIT_COMMIT_MSG=Release %NEW_VER%"
echo.
echo [Step 6/7] Committing: "%GIT_COMMIT_MSG%"
git commit -m "%GIT_COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo [Error] Git commit failed. You may need to stage and commit manually.
    exit /b 1
)

:: --- 7. Tag ---
echo.
echo [Step 7/7] Tagging release: %NEW_VER%
git tag "LOG_ANALYZER_%NEW_VER%"
if %errorlevel% neq 0 (
    echo [Error] Git tag failed. You may need to create the tag manually.
    exit /b 1
)

echo.
echo ========================================================
echo  Release process for %NEW_VER% completed successfully!
echo ========================================================
echo.
echo Final artifacts:
echo   - %NEW_EXE_FILE%
echo   - %NEW_TAR_FILE%
echo   - %NEW_HTML_FILE%
echo.

endlocal
