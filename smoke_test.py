import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

def test_import():
    print("Testing import of LogAnalyzerApp...")
    try:
        # Try importing the main app class
        from log_analyzer.app import LogAnalyzerApp
        print("SUCCESS: LogAnalyzerApp imported successfully.")
        return True
    except Exception:
        print("FAILURE: Could not import LogAnalyzerApp.")
        traceback.print_exc()
        return False

def check_syntax(start_dir="log_analyzer"):
    print(f"\nChecking syntax in {start_dir}...")
    import compileall
    try:
        # compile_dir returns True if success, False if errors
        # quiet=1: do not print list of compiled files
        if compileall.compile_dir(start_dir, quiet=1, force=True):
            print("SUCCESS: No syntax errors found.")
            return True
        else:
            print("FAILURE: Syntax errors found.")
            return False
    except Exception:
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import_ok = test_import()
    syntax_ok = check_syntax()

    if import_ok and syntax_ok:
        sys.exit(0)
    else:
        sys.exit(1)
