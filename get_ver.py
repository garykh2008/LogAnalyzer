import re
import os

# Updated to point to the new location of the version string
PYTHON_FILE = os.path.join('log_analyzer', 'app.py')

def get_version():
	"""
	Reads the version from the main python file.
	Returns the version string (e.g., "v1.2") or "Unknown".
	"""
	if not os.path.exists(PYTHON_FILE):
		return "Unknown"

	try:
		with open(PYTHON_FILE, 'r', encoding='utf-8') as f:
			content = f.read()
			# Find self.VERSION = "..."
			m = re.search(r'self\.VERSION\s*=\s*["\']([^"\']+)["\']', content)
			if m:
				return m.group(1)
			else:
				return "Unknown"
	except Exception:
		return "Unknown"

if __name__ == "__main__":
	print(get_version())
