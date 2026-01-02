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

# 2. Check and Install Python3-tk
if python3 -c "import tkinter" &>/dev/null; then
    echo -e "${GREEN}[V] Python3-tk is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3-tk not found. Attempting to install...${NC}"

    sudo apt-get install -y python3-tk

    if python3 -c "import tkinter" &>/dev/null; then
        echo -e "${GREEN}[V] Python3-tk installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install Python3-tk.${NC}"
        exit 1
    fi
fi

# 3. Check and Install Python3-pip (Robust Fallback Strategy)
if python3 -m pip --version &>/dev/null; then
    echo -e "${GREEN}[V] pip is already installed.${NC}"
else
    echo -e "${YELLOW}[!] pip not found. Attempting to install...${NC}"

    # Strategy A: Try apt-get
    echo -e "${YELLOW}Method 1: Attempting apt-get install python3-pip...${NC}"
    sudo apt-get update
    if sudo apt-get install -y python3-pip; then
        echo -e "${GREEN}[V] Installed via apt-get.${NC}"
    else
        echo -e "${YELLOW}[!] apt-get failed. Method 2: Attempting ensurepip...${NC}"

        # Strategy B: Try ensurepip (Standard Library)
        if python3 -m ensurepip --upgrade; then
            echo -e "${GREEN}[V] Installed via ensurepip.${NC}"
        else
            echo -e "${YELLOW}[!] ensurepip failed. Method 3: Downloading get-pip.py...${NC}"

            # Strategy C: Download get-pip.py
            if ! command -v curl &>/dev/null; then
                 sudo apt-get install -y curl
            fi

            if curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py; then
                if python3 get-pip.py; then
                    echo -e "${GREEN}[V] Installed via get-pip.py.${NC}"
                    rm get-pip.py
                else
                    echo -e "${RED}[X] Failed to run get-pip.py.${NC}"
                    rm get-pip.py
                    exit 1
                fi
            else
                echo -e "${RED}[X] Failed to download get-pip.py.${NC}"
                exit 1
            fi
        fi
    fi

    # Final Verification
    if python3 -m pip --version &>/dev/null; then
        echo -e "${GREEN}[V] pip installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install pip. Please check your environment.${NC}"
        exit 1
    fi
fi

# 4. Check and Install Python3-venv (Required for building release)
if python3 -c "import venv" &>/dev/null; then
    echo -e "${GREEN}[V] Python3-venv is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3-venv not found. Attempting to install...${NC}"

    sudo apt-get install -y python3-venv

    if python3 -c "import venv" &>/dev/null; then
        echo -e "${GREEN}[V] Python3-venv installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install Python3-venv. This is often a separate package on Debian/Ubuntu.${NC}"
        # Fallback suggestion, but venv is harder to bootstrap without apt
        exit 1
    fi
fi

# 5. Check and Install Rust (Required for extension)
# Determine real user home if running as sudo
if [ -n "$SUDO_USER" ]; then
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_HOME=$HOME
fi

if [ -f "$REAL_HOME/.cargo/bin/cargo" ] || command -v cargo &>/dev/null; then
    echo -e "${GREEN}[V] Rust (cargo) is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Rust not found. Attempting to install via rustup...${NC}"

    # Ensure curl is present
    if ! command -v curl &>/dev/null; then
        echo -e "${YELLOW}Installing curl...${NC}"
        sudo apt-get install -y curl
    fi

    if [ -n "$SUDO_USER" ]; then
        echo -e "${YELLOW}Detected sudo. Installing Rust for user: $SUDO_USER${NC}"
        # Download and install as the sudo user
        sudo -u "$SUDO_USER" sh -c "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
    else
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    fi

    echo -e "${GREEN}[V] Rust installed. You may need to restart your shell or run 'source \$HOME/.cargo/env'.${NC}"
fi

# 6. Install Python dependencies (including Flet)
echo -e "${YELLOW}[!] Installing/Updating Python libraries (flet, maturin, pyinstaller)...${NC}"
python3 -m pip install flet maturin pyinstaller markdown

echo -e "${GREEN}--- All checks completed successfully ---${NC}"
