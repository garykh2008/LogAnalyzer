import re
import os

# 目標檔案
PYTHON_FILE = 'loganalyzer.py'

def main():
	if not os.path.exists(PYTHON_FILE):
		print("Unknown")
		return

	try:
		with open(PYTHON_FILE, 'r', encoding='utf-8') as f:
			content = f.read()
			# 尋找 self.VERSION = "..."
			m = re.search(r'self\.VERSION\s*=\s*["\']([^"\']+)["\']', content)
			if m:
				print(m.group(1))
			else:
				print("Unknown")
	except Exception:
		print("Unknown")

if __name__ == "__main__":
	main()