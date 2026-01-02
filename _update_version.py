import sys
import re
import os

def update_version(new_version):
    # Updated to point to the new location
    file_path = os.path.join('log_analyzer', 'app.py')
    
    if not os.path.exists(file_path):
        print(f"[Error] Target file not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # A robust regex to find and replace the version
        # Looks for: self.VERSION = "anything" or self.VERSION="anything"
        # Handles single or double quotes.
        pattern = r'(self\.VERSION\s*=\s*["\']).*?(["\'])'
        replacement = r'\g<1>{}\g<2>'.format(new_version)
        
        # Use re.subn to get the number of substitutions made
        new_content, count = re.subn(pattern, replacement, content)

        if count == 0:
            print(f"[Error] Could not find a line matching 'self.VERSION = ...' in {file_path}.")
            sys.exit(1)
        
        if new_content == content:
            print("[Warning] File content did not change. Is the version already set correctly?")
            pass

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
    except Exception as e:
        print(f"[Error] An unexpected error occurred while updating version: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[Error] No new version number provided to update script.")
        sys.exit(1)
    
    update_version(sys.argv[1])
