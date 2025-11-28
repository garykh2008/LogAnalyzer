#!/bin/bash
# Log Analyzer Launcher

# 1. Check Python
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}[V] Python3 is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3 not found. Run install_deps.sh to install dependencies.${NC}"
    exit 1
fi

if python3 -c "import tkinter" &>/dev/null; then
    echo -e "${GREEN}[V] Python3-tk is already installed.${NC}"
else
    echo -e "${YELLOW}[!] Python3-tk not found. Run install_deps.sh to install dependencies.${NC}"
    exit 1
fi

# 2. Run App
# Ensure we run the script in the correct directory
cd "$(dirname "$0")"
python3 loganalyzer.py