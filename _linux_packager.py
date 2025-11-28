import os
import tarfile
import shutil
import re

# Configuration
MAIN_SCRIPT = "loganalyzer.py"
DOC_DIR = "Doc"
LINUX_SCRIPTS = ["run_loganalyzer.sh", "install_deps.sh"]
RELEASE_DIR = os.path.join("release", "linux")
TEMP_DIR = os.path.join(RELEASE_DIR, "temp_build")

def get_version():
	if not os.path.exists(MAIN_SCRIPT):
		return "Unknown"
	with open(MAIN_SCRIPT, 'r', encoding='utf-8') as f:
		content = f.read()
		# Match: self.VERSION = "v1.0"
		m = re.search(r'self\.VERSION\s*=\s*["\']([^"\']+)["\']', content)
		if m:
			return m.group(1)
	return "Unknown"

def create_linux_package():
	print("[Linux Packager] Starting...")

	version = get_version()
	print(f"[Linux Packager] Detected version: {version}")

	# 1. Prepare Paths
	if not os.path.exists(RELEASE_DIR):
		os.makedirs(RELEASE_DIR)

	if os.path.exists(TEMP_DIR):
		shutil.rmtree(TEMP_DIR)
	os.makedirs(TEMP_DIR)

	try:
		# 2. Copy Main Script
		print(f"[Linux Packager] Copying {MAIN_SCRIPT}...")
		shutil.copy(MAIN_SCRIPT, TEMP_DIR)

		# 3. Copy Documentation
		if os.path.exists(DOC_DIR):
			print(f"[Linux Packager] Copying {DOC_DIR}...")
			shutil.copytree(DOC_DIR, os.path.join(TEMP_DIR, DOC_DIR))
		else:
			print(f"[Linux Packager] Warning: {DOC_DIR} not found.")

		# 4. Process Linux Scripts (Enforce LF line endings)
		# This is crucial when packaging from Windows!
		for script in LINUX_SCRIPTS:
			if os.path.exists(script):
				print(f"[Linux Packager] Processing {script} (converting CRLF to LF)...")
				with open(script, 'r', encoding='utf-8') as f_in:
					content = f_in.read()

				# Write to temp dir with forced Unix newline
				dest_path = os.path.join(TEMP_DIR, script)
				with open(dest_path, 'w', encoding='utf-8', newline='\n') as f_out:
					f_out.write(content)
			else:
				print(f"[Linux Packager] Error: {script} not found in source directory!")

		# 5. Create Tarball
		tar_filename = f"LogAnalyzer_{version}_Linux.tar.gz"
		tar_path = os.path.join(RELEASE_DIR, tar_filename)

		print(f"[Linux Packager] Creating tarball: {tar_filename}...")
		with tarfile.open(tar_path, "w:gz") as tar:
			# arcname sets the internal folder name
			tar.add(TEMP_DIR, arcname=f"LogAnalyzer_{version}")

		print(f"[Linux Packager] Success! Package saved to: {tar_path}")

	except Exception as e:
		print(f"[Linux Packager] Error: {e}")
	finally:
		# 6. Cleanup
		if os.path.exists(TEMP_DIR):
			shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
	create_linux_package()