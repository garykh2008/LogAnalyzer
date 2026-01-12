#!/bin/bash

# Define colors for clearer output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting dependency check for Log Analyzer (Qt)...${NC}"

# 1. Check and Install Python3
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}[V] Python3 is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3 not found. Attempting to install...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3
fi

# 2. Check and Install Python3-pip and Venv
if ! command -v pip3 &>/dev/null; then
    echo -e "${YELLOW}[!] pip3 not found. Installing...${NC}"
    sudo apt-get install -y python3-pip
fi

if ! python3 -c "import venv" &>/dev/null; then
    echo -e "${YELLOW}[!] python3-venv not found. Installing...${NC}"
    sudo apt-get install -y python3-venv
fi

# 3. Check and Install Rust (Required for extension)
if command -v cargo &>/dev/null; then
    echo -e "${GREEN}[V] Rust (cargo) is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Rust not found. Attempting to install via rustup...${NC}"
    if ! command -v curl &>/dev/null; then
        sudo apt-get install -y curl
    fi
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 4. Install Python Dependencies (PySide6)
echo -e "${YELLOW}[*] Installing Python dependencies (PySide6, maturin)...${NC}"
# Use --break-system-packages if on newer Debian/Ubuntu, or standard pip
pip3 install PySide6 maturin --break-system-packages 2>/dev/null || pip3 install PySide6 maturin

echo -e "${GREEN}--- All checks completed successfully ---${NC}"
