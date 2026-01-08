import sys
import os
import signal
import argparse
import glob
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtCore import Qt, qInstallMessageHandler, QtMsgType
from qt_app.ui import MainWindow
from qt_app.utils import load_custom_fonts

def qt_message_handler(mode, context, message):
    if "Point size <= 0" in message:
        return # Suppress this specific known benign warning
    
    # Simple default printing for other messages
    if mode == QtMsgType.QtInfoMsg: mode_str = "Info"
    elif mode == QtMsgType.QtWarningMsg: mode_str = "Warning"
    elif mode == QtMsgType.QtCriticalMsg: mode_str = "Critical"
    elif mode == QtMsgType.QtFatalMsg: mode_str = "Fatal"
    else: mode_str = "Debug"
    print(f"[{mode_str}] {message}")

def main():
    # Parse CLI Arguments
    parser = argparse.ArgumentParser(description="Log Analyzer Qt")
    parser.add_argument("logs", nargs="*", help="Log files to open (supports wildcards like *.log)")
    parser.add_argument("-f", "--filter", help="Load a .tat filter file on startup")
    
    # Handle @filelist for long argument lists
    args = parser.parse_args()

    # Install custom message handler
    qInstallMessageHandler(qt_message_handler)

    # Allow Ctrl+C to terminate the app from console
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 1. High DPI Scaling is enabled by default in Qt 6 / PySide6.
    app = QApplication(sys.argv)

    # 2. Load Custom Fonts (Inter)
    load_custom_fonts()

    # 3. Set Application-wide Font Strategy
    font = QFont("Inter")
    font.setStyleStrategy(QFont.PreferAntialias)
    if "Inter" not in QFontDatabase.families():
        font.setFamily("Segoe UI") 
    
    font.setPixelSize(12)
    app.setFont(font)

    # Set organization info for QSettings
    app.setOrganizationName("LogAnalyzer")
    app.setApplicationName("Log Analyzer Qt")

    window = MainWindow()

    # Process CLI Filter
    if args.filter and os.path.exists(args.filter):
        window.load_tat_filter_from_cli(args.filter)

    # Process CLI Logs (with Wildcard Expansion)
    expanded_logs = []
    for pattern in args.logs:
        matches = glob.glob(pattern)
        if matches:
            expanded_logs.extend(matches)
        else:
            expanded_logs.append(pattern) # Fallback to original if no glob match

    if expanded_logs:
        window.load_logs_from_cli(expanded_logs)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
