#!/bin/bash
set -e

echo "[Linux Build] Starting..."
PROJECT_ROOT=$(pwd)

# 1. Install Dependencies
echo "[Linux Build] Setting up virtual environment..."
if ! python3 -c "import venv" &>/dev/null; then
    echo "[Linux Build] Error: python3-venv module not found."
    echo "Please install it (e.g., 'sudo apt install python3-venv' on Ubuntu/Debian)."
    exit 1
fi

# Check for tkinter (Required for tkinterdnd2)
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "[Linux Build] Error: tkinter module not found."
    echo "Please install it (e.g., 'sudo apt install python3-tk' on Ubuntu/Debian)."
    exit 1
fi

# Use a temporary directory for venv to avoid WSL/NTFS permission issues
VENV_BASE=$(mktemp -d)
VENV_DIR="$VENV_BASE/build_venv"

echo "[Linux Build] Creating virtual environment at $VENV_DIR..."
if ! python3 -m venv "$VENV_DIR"; then
    echo "[Linux Build] Standard venv creation failed. Retrying with --without-pip..."
    rm -rf "$VENV_DIR"
    # Try without pip (bypasses ensurepip error common on Debian/Ubuntu)
    if ! python3 -m venv "$VENV_DIR" --without-pip; then
        echo "[Linux Build] Error: Failed to create virtual environment."
        echo "Please ensure 'python3-venv' is installed: sudo apt install python3-venv"
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
    
    echo "[Linux Build] Bootstrapping pip..."
    # Download get-pip.py using python to avoid curl/wget dependencies
    python3 -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
    python3 get-pip.py
    rm get-pip.py
else
    source "$VENV_DIR/bin/activate"
fi

echo "[Linux Build] Installing Python dependencies into venv..."
pip install pyinstaller markdown tkinterdnd2 maturin

# Check for Rust
SKIP_RUST=0
echo "[Linux Build] Checking for Rust environment..."
if ! command -v cargo &> /dev/null; then
    echo "[Linux Build] Warning: Rust compiler (cargo) not found. Rust extension build will be skipped."
    SKIP_RUST=1
fi

# 2. Build Rust Extension
if [ "$SKIP_RUST" -eq 0 ]; then
echo "[Linux Build] Building Rust extension..."
if [ -d "rust_extention" ]; then
    # Copy Rust source to temp dir to avoid WSL/NTFS permission issues
    RUST_BUILD_DIR="$VENV_BASE/rust_build"
    cp -r "rust_extention" "$RUST_BUILD_DIR"
    cd "$RUST_BUILD_DIR"

    # Clean artifacts copied from Windows to avoid installing wrong wheel
    rm -rf target

    # Set environment variable for compatibility
    export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
    maturin build --release

    # Install the wheel
    # Find the wheel file
    WHEEL_FILE=$(find target/wheels -name "*.whl" | head -n 1)
    if [ -n "$WHEEL_FILE" ]; then
        echo "[Linux Build] Installing Rust wheel: $WHEEL_FILE"
        pip install "$WHEEL_FILE" --force-reinstall
    else
        echo "[Linux Build] Error: Rust wheel not found!"
        exit 1
    fi
    cd "$PROJECT_ROOT"
else
    echo "[Linux Build] Warning: rust_extention directory not found."
fi
else
    echo "[Linux Build] Skipping Rust extension build (Rust not found)."
fi

# 3. Build Docs
echo "[Linux Build] Building documentation..."
python3 build_docs.py

# 4. Get Version (for naming)
VERSION=$(python3 get_ver.py)
echo "[Linux Build] Detected version: $VERSION"

# 5. PyInstaller
echo "[Linux Build] Running PyInstaller..."
TKINTERDND2_PATH=$(python3 -c "import os, tkinterdnd2; print(os.path.abspath(os.path.dirname(tkinterdnd2.__file__)))")
ABS_PATH=$(pwd)

# Use temp directories for build artifacts to avoid WSL/NTFS permission issues (chmod)
TEMP_DIST="$VENV_BASE/dist"
TEMP_WORK="$VENV_BASE/build"

mkdir -p release/linux

# Note: Separator is ':' for Linux
pyinstaller --noconfirm --noconsole --onefile --clean \
    --distpath "$TEMP_DIST" \
    --workpath "$TEMP_WORK" \
    --specpath "$TEMP_WORK" \
    --add-data "$ABS_PATH/Doc:Doc" \
    --add-data "$TKINTERDND2_PATH:tkinterdnd2" \
    --add-data "$ABS_PATH/loganalyzer.ico:." \
    --icon="$ABS_PATH/loganalyzer.ico" \
    --hidden-import log_engine_rs \
    --name "LogAnalyzer_Linux_${VERSION}" \
    "loganalyzer.py"

# Copy the binary back to the project directory
echo "[Linux Build] Copying binary to release/linux/..."
cp "$TEMP_DIST/LogAnalyzer_Linux_${VERSION}" "release/linux/"

echo "[Linux Build] Success! Executable is in release/linux/"
echo "File: release/linux/LogAnalyzer_Linux_${VERSION}"