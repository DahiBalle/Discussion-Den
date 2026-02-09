import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

print("Attempting validation of imports...")

try:
    # Try importing extensions from root
    import extensions
    print("SUCCESS: extensions imported successfully")
except ImportError as e:
    print(f"IMPORT ERROR: extensions: {e}")

try:
    # Try importing routes from root
    import routes.api
    print("SUCCESS: routes.api imported successfully")
except ImportError as e:
    print(f"IMPORT ERROR: routes.api: {e}")

try:
    # Try importing app (which is now a module, not a package, so this might import the file app.py)
    import app
    print("SUCCESS: app imported successfully")
except ImportError as e:
    print(f"IMPORT ERROR: app: {e}")

print("Verification script finished.")
