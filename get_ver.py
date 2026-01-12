import re
import os

QT_UI_FILE = os.path.join('qt_app', 'ui.py')

def get_version():
    """
    Reads the version from qt_app/ui.py.
    Returns the version string (e.g., "V2.0") or "Unknown".
    """
    if os.path.exists(QT_UI_FILE):
        try:
            with open(QT_UI_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Match: VERSION = "V2.0"
            m = re.search(r'VERSION\s*=\s*["\']([^"\\]+)["\\]', content)
            if m:
                return m.group(1)
        except Exception:
            pass

    return "Unknown"

if __name__ == "__main__":
    print(get_version())