
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Verify required packages are installed before launching."""
    missing = []
    packages = {
        "numpy": "numpy",
        "scipy": "scipy",
        "matplotlib": "matplotlib",
        "customtkinter": "customtkinter",
    }
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print("=" * 60)
        print("CuffnCode — Missing Dependencies")
        print("=" * 60)
        print("Please install the required packages by running:")
        print(f"\n  pip install {' '.join(missing)}\n")
        print("Or install all at once:")
        print("\n  pip install -r requirements.txt\n")
        sys.exit(1)

def main():
    check_dependencies()
    from gui.dashboard import CuffnCodeApp
    app = CuffnCodeApp()
    app.mainloop()

if __name__ == "__main__":
    main()
