import sys
import os
import signal
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
    # Install custom message handler
    qInstallMessageHandler(qt_message_handler)

    # Allow Ctrl+C to terminate the app from console
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 1. High DPI Scaling is enabled by default in Qt 6 / PySide6.
    # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps.

    app = QApplication(sys.argv)

    # 2. Load Custom Fonts (Inter)
    load_custom_fonts()

    # 3. Set Application-wide Font Strategy
    # Priority: Inter -> Segoe UI -> System Default
    font = QFont("Inter")
    font.setStyleStrategy(QFont.PreferAntialias)
    # Fallback to system fonts if Inter isn't installed/loaded
    if "Inter" not in QFontDatabase.families():
        font.setFamily("Segoe UI") 
    
    # Set default size (point size 9 is usually good for desktop apps ~12px)
    font.setPointSize(9) 
    app.setFont(font)

    # Set organization info for QSettings
    app.setOrganizationName("LogAnalyzer")
    app.setApplicationName("Log Analyzer Qt")

    window = MainWindow()

    # Check command line args for file
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            window.load_log(filepath)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
