#!/bin/bash

# Define colors for clearer output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting check for dependencies...${NC}"

# 1. Check and Install Python3
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}[V] Python3 is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3 not found. Attempting to install...${NC}"

    # Update package list and install python3
    sudo apt-get update
    sudo apt-get install -y python3

    # Verify installation
    if command -v python3 &>/dev/null; then
        echo -e "${GREEN}[V] Python3 installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install Python3. Please check your internet or permissions.${NC}"
        exit 1
    fi
fi

# 2. Check and Install Python3-tk (Removed as Flet doesn't require it for core function, but sometimes useful for dialogs fallback)
# Keeping it optional or removing strict check

# 3. Check and Install Python3-venv (Required for building release)
if python3 -c "import venv" &>/dev/null; then
    echo -e "${GREEN}[V] Python3-venv is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3-venv not found. Attempting to install...${NC}"

    sudo apt-get install -y python3-venv

    if python3 -c "import venv" &>/dev/null; then
        echo -e "${GREEN}[V] Python3-venv installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install Python3-venv.${NC}"
        exit 1
    fi
fi

# 4. Check and Install Rust (Required for extension)
if command -v cargo &>/dev/null; then
    echo -e "${GREEN}[V] Rust (cargo) is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Rust not found. Attempting to install via rustup...${NC}"

    # Ensure curl is present
    if ! command -v curl &>/dev/null; then
        echo -e "${YELLOW}Installing curl...${NC}"
        sudo apt-get install -y curl
    fi

    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    echo -e "${GREEN}[V] Rust installed. You may need to restart your shell or run 'source \$HOME/.cargo/env'.${NC}"
fi

# 5. Install Python dependencies (including Flet)
echo -e "${YELLOW}[!] Installing/Updating Python libraries (flet, maturin, pyinstaller)...${NC}"
pip3 install flet maturin pyinstaller markdown

echo -e "${GREEN}--- All checks completed successfully ---${NC}"
