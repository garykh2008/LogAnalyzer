#!/bin/bash

# Define colors for clearer output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting check for Python3 and Python3-tk...${NC}"

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
# We check by trying to import the 'tkinter' module inside python
if python3 -c "import tkinter" &>/dev/null; then
    echo -e "${GREEN}[V] Python3-tk is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3-tk not found. Attempting to install...${NC}"
    
    sudo apt-get install -y python3-tk

    # Verify installation
    if python3 -c "import tkinter" &>/dev/null; then
        echo -e "${GREEN}[V] Python3-tk installed successfully.${NC}"
    else
        echo -e "${RED}[X] Failed to install Python3-tk.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}--- All checks completed successfully ---${NC}"