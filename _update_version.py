import sys
import re
import os

def update_version(new_version):
    files_to_check = [os.path.join('qt_app', 'ui.py'), 'loganalyzer.py']
    updated_any = False

    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Regex based on file type
            if 'ui.py' in file_path:
                pattern = r'(VERSION\s*=\s*["\']).*?(["\'])'
            else:
                pattern = r'(self\.VERSION\s*=\s*["\']).*?(["\'])'
            
            replacement = r'\g<1>{}\g<2>'.format(new_version)
            
            new_content, count = re.subn(pattern, replacement, content)

            if count > 0 and new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"[Info] Updated version in {file_path}")
                updated_any = True
            elif count == 0:
                print(f"[Warning] Version pattern not found in {file_path}")

        except Exception as e:
            print(f"[Error] Failed to update {file_path}: {e}")
            sys.exit(1)
            
    if not updated_any:
        print("[Error] No files were updated.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[Error] No new version number provided.")
        sys.exit(1)
    
    update_version(sys.argv[1])
