import flet as ft
import sys
import os
import warnings

# Suppress DeprecationWarnings from Flet 1.0 if any
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure the current directory is in sys.path so the 'log_analyzer' package can be found
sys.path.append(os.getcwd())

from log_analyzer.main import main

if __name__ == "__main__":
    ft.run(main)
