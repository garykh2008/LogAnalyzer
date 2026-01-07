#!/bin/bash
set -e

echo "[Linux Build] Starting..."
PROJECT_ROOT=$(pwd)

# 1. Install Dependencies
echo "[Linux Build] Setting up virtual environment..."
if ! python3 -c "import venv" &>/dev/null; then
    echo "[Linux Build] Error: python3-venv module not found."
    echo "Please run './install_deps.sh' to install system dependencies."
    exit 1
fi

# Use a temporary directory for venv to avoid WSL/NTFS permission issues
VENV_BASE=$(mktemp -d)
VENV_DIR="$VENV_BASE/build_venv"

echo "[Linux Build] Creating virtual environment at $VENV_DIR..."
if ! python3 -m venv "$VENV_DIR"; then
    echo "[Linux Build] Standard venv creation failed. Retrying with --without-pip..."
    rm -rf "$VENV_DIR"
    if ! python3 -m venv "$VENV_DIR" --without-pip; then
        echo "[Linux Build] Error: Failed to create virtual environment."
        echo "Please ensure 'python3-venv' is installed: sudo apt install python3-venv"
        exit 1
    fi
    source "$VENV_DIR/bin/activate"

    echo "[Linux Build] Bootstrapping pip..."
    python3 -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
    python3 get-pip.py
    rm get-pip.py
else
    source "$VENV_DIR/bin/activate"
fi

echo "[Linux Build] Installing Python dependencies into venv..."
pip install pyinstaller markdown maturin PySide6

# Check for Rust
echo "[Linux Build] Checking for Rust environment..."
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
fi

if ! command -v cargo &> /dev/null; then
    echo "[Linux Build] Error: Rust compiler (cargo) not found."
    exit 1
fi

# 2. Build Rust Extension
echo "[Linux Build] Updating Rust extension..."
chmod +x update_rust.sh
./update_rust.sh

# 3. Build Docs
echo "[Linux Build] Building documentation..."
python3 build_docs.py

# 4. Get Version
VERSION=$(python3 get_ver.py)
echo "[Linux Build] Detected version: $VERSION"

# 5. PyInstaller
echo "[Linux Build] Running PyInstaller..."
ABS_PATH=$(pwd)
TEMP_DIST="$VENV_BASE/dist"
TEMP_WORK="$VENV_BASE/build"

mkdir -p release/linux

# Build Qt App
# We point to qt_app/main.py but need to ensure it can import qt_app package or relative imports work.
# PyInstaller usually handles 'qt_app/main.py' correctly if run from root.
pyinstaller --noconfirm --noconsole --onefile --clean \
    --distpath "$TEMP_DIST" \
    --workpath "$TEMP_WORK" \
    --specpath "$TEMP_WORK" \
    --add-data "$ABS_PATH/Doc:Doc" \
    --add-data "$ABS_PATH/loganalyzer.ico:." \
    --icon="$ABS_PATH/loganalyzer.ico" \
    --hidden-import log_engine_rs \
    --name "LogAnalyzer_Linux_${VERSION}" \
    "qt_app/main.py"

# Copy binary
echo "[Linux Build] Copying binary to release/linux/..."
cp "$TEMP_DIST/LogAnalyzer_Linux_${VERSION}" "release/linux/"

echo "[Linux Build] Success! Executable is in release/linux/"
echo "File: release/linux/LogAnalyzer_Linux_${VERSION}"