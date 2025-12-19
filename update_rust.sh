#!/bin/bash
set -e

# Determine pip arguments for system packages (PEP 668)
PIP_ARGS=""
if [ -z "$VIRTUAL_ENV" ]; then
    # Only check if not in a virtual environment
    if pip install --help | grep -q "break-system-packages"; then
        echo "[Rust Update] Detected externally managed environment. Using --break-system-packages."
        PIP_ARGS="--break-system-packages"
    fi
fi

echo "[Rust Update] Checking for Rust environment..."
if ! command -v cargo &> /dev/null; then
    echo "[Rust Update] Error: Rust compiler (cargo) not found."
    exit 1
fi

# Check for maturin
if ! command -v maturin &> /dev/null; then
    echo "[Rust Update] maturin not found. Installing..."
    pip install maturin $PIP_ARGS

    # Add ~/.local/bin to PATH if maturin was installed there
    if ! command -v maturin &> /dev/null && [ -d "$HOME/.local/bin" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

if [ ! -d "rust_extention" ]; then
    echo "[Rust Update] Error: rust_extention directory not found."
    exit 1
fi

# Create temp dir for building to avoid WSL/NTFS locking/perf issues
BUILD_BASE=$(mktemp -d)
echo "[Rust Update] Using temp build directory: $BUILD_BASE"

cp -r "rust_extention" "$BUILD_BASE/"
cd "$BUILD_BASE/rust_extention"

# Clean artifacts to ensure clean build
rm -rf target

echo "[Rust Update] Building Rust extension..."
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
maturin build --release

# Find and install wheel
WHEEL_FILE=$(find target/wheels -name "*.whl" | head -n 1)
if [ -n "$WHEEL_FILE" ]; then
    echo "[Rust Update] Installing Rust wheel: $WHEEL_FILE"
    pip install "$WHEEL_FILE" --force-reinstall $PIP_ARGS
else
    echo "[Rust Update] Error: Rust wheel not found!"
    exit 1
fi

# Cleanup
cd - > /dev/null
rm -rf "$BUILD_BASE"
echo "[Rust Update] Done."