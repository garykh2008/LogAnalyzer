import sys
import os
import signal
from PySide6.QtWidgets import QApplication
from qt_app.ui import MainWindow

def main():
    # Allow Ctrl+C to terminate the app from console
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)

    # Set organization info for QSettings (if used later)
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
