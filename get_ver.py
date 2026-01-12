import re
import os

QT_UI_FILE = os.path.join('qt_app', 'ui.py')
LEGACY_FILE = 'loganalyzer.py'

def get_version():
	"""
	Reads the version from the main python files.
	Returns the version string (e.g., "V2.0") or "Unknown".
	"""
	# Priority 1: QT Version
	if os.path.exists(QT_UI_FILE):
		try:
			with open(QT_UI_FILE, 'r', encoding='utf-8') as f:
				content = f.read()
				m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
				if m: return m.group(1)
		except Exception: pass

	# Priority 2: Legacy Version
	if os.path.exists(LEGACY_FILE):
		try:
			with open(LEGACY_FILE, 'r', encoding='utf-8') as f:
				content = f.read()
				m = re.search(r'self\.VERSION\s*=\s*["\']([^"\']+)["\']', content)
				if m: return m.group(1)
		except Exception: pass

	return "Unknown"

if __name__ == "__main__":
	print(get_version())