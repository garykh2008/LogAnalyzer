:: --- Dependency Check & Install ---
echo [Init] Checking and installing dependencies...
pip install pyinstaller markdown maturin PySide6
if %errorlevel% neq 0 (
    echo [Error] Failed to install dependencies.
    exit /b 1
)

:: --- Check for Rust ---
echo [Init] Checking for Rust environment...
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Rust compiler ^(cargo^) not found. Rust is now a required dependency.
    echo Please install the Rust toolchain: https://www.rust-lang.org/tools/install
    exit /b 1
)
:: --- Mode Selection ---
if /I "%~1" == "/buildonly" goto :build_only_mode
:: Check for no parameter
if "%~1" == "" (
    echo [Error] No parameter provided.
    echo Usage for full release: %~nx0 vX.Y
    echo Usage for build only:   %~nx0 /buildonly
    exit /b 1
)
:: Check if parameter starts with 'v' (case-insensitive)
set "PARAM=%~1"
if /I "!PARAM:~0,1!" == "v" goto :full_release_mode

:: If we reach here, the parameter is invalid
echo [Error] Invalid parameter: %~1
echo Usage for full release: %~nx0 vX.Y
echo Usage for build only:   %~nx0 /buildonly
exit /b 1


:: --- 1. Version Check & Setup ---
:full_release_mode
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
echo [Step 2/7] Updating version in source...
python _update_version.py %NEW_VER%
if %errorlevel% neq 0 (
    echo [Error] Failed to update version number using _update_version.py.
    exit /b 1
)
echo      Successfully updated version to %NEW_VER%.

:: --- 4. Build, Commit, and Tag ---
echo.
echo [Step 3/7] Starting build process for %NEW_VER%...
call :build_process %NEW_VER%
if %errorlevel% neq 0 (
    echo [Error] Build process failed.
    exit /b 1
)

echo      Build complete for %NEW_VER%.

:: --- 5. Git Operations ---
echo.
echo [Step 5/7] Staging files for commit...

:: Define old/new filenames
set "OLD_HTML_FILE=Doc\Log_Analyzer_%OLD_VER%_Docs_EN.html"
set "NEW_HTML_FILE=Doc\Log_Analyzer_%NEW_VER%_Docs_EN.html"
set "NEW_EXE_FILE=release\windows\LogAnalyzer_%NEW_VER%.exe"

:: Remove old documentation file from Git index if it exists and filenames differ
if exist "%OLD_HTML_FILE%" (
    if /I "%OLD_HTML_FILE%" neq "%NEW_HTML_FILE%" (
        echo      Removing old doc file from Git: %OLD_HTML_FILE%
        git rm "%OLD_HTML_FILE%" > nul
    )
)

:: Add all new/modified files
echo      Adding new release files to Git...
git add qt_app/ui.py "%NEW_HTML_FILE%"
git add "%NEW_HTML_FILE%"

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
echo   - %NEW_HTML_FILE%
echo.

endlocal
goto :eof


:: ============================================================================
::                            BUILD ONLY MODE
:: ============================================================================
:build_only_mode
echo --- Starting Build-Only Mode ---
echo.

:: 1. Get Current Version
echo [Step 1/2] Reading current version...
for /f "delims=" %%i in ('python get_ver.py') do set "CURRENT_VER=%%i"
if "%CURRENT_VER%"=="Unknown" (
    echo [Error] Could not determine current version from get_ver.py. Aborting.
    exit /b 1
)
echo      Current version is %CURRENT_VER%.

:: 2. Build
echo.
echo [Step 2/2] Starting build process for %CURRENT_VER%...
call :build_process %CURRENT_VER%
if %errorlevel% neq 0 (
    echo [Error] Build process failed.
    exit /b 1
)

echo.
echo ========================================================
echo  Build-Only process for %CURRENT_VER% completed successfully!
echo ========================================================
echo.

endlocal
goto :eof


:: ============================================================================
::                         SHARED BUILD PROCESS
:: ============================================================================
:build_process
set "BUILD_VER=%~1"

set "PYTHON_FILE=qt_app/main.py"
set "DOC_SCRIPT=build_docs.py"
set "DOC_DIR=Doc"
set "REL_WIN=release\windows"

echo      [Build] Updating Rust Extension...
call update_rust.bat
if %errorlevel% neq 0 (
    echo [Error] Failed to update Rust extension.
    exit /b 1
)

echo      [Build] Building documentation...
python "%DOC_SCRIPT%"

echo      [Build] Building Windows Executable...
if not exist "%REL_WIN%" mkdir "%REL_WIN%"
if not exist "build" mkdir "build"
set "ABS_DOC_SRC=%~dp0%DOC_DIR%"
set "ABS_ICON_PATH=%~dp0loganalyzer.ico"
set "ABS_FONTS_SRC=%~dp0qt_app\fonts"
pyinstaller --noconfirm --noconsole --onefile --clean --distpath "%REL_WIN%" --workpath "build" --specpath "build" --add-data "%ABS_DOC_SRC%;%DOC_DIR%" --add-data "%ABS_FONTS_SRC%;qt_app/fonts" --add-data "%ABS_ICON_PATH%;." --icon="%ABS_ICON_PATH%" --hidden-import log_engine_rs --name "LogAnalyzer_%BUILD_VER%" "%PYTHON_FILE%" > build/pyinstaller.log 2>&1
if %errorlevel% neq 0 ( echo [Error] PyInstaller failed. Check build/pyinstaller.log && exit /b 1 )

goto :eof