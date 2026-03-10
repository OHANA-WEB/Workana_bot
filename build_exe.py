"""
Build script to create a standalone .exe file for the Workana bot.
Run: python build_exe.py
"""
import subprocess
import sys
from pathlib import Path

def build_exe():
    """Build the executable using PyInstaller."""
    script_dir = Path(__file__).parent
    
    print("Building executable with PyInstaller...")
    print("=" * 60)
    
    # Use the spec file for better control
    # Use python -m PyInstaller to avoid PATH issues
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "workana_bot.spec"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, cwd=script_dir)
        print("\n" + "=" * 60)
        print("[SUCCESS] Build successful!")
        exe_path = script_dir / 'dist' / 'workana_bot.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Executable location: {exe_path}")
            print(f"File size: {size_mb:.2f} MB")
        print("\n" + "=" * 60)
        print("IMPORTANT NOTES:")
        print("1. Copy the .env file to the same folder as workana_bot.exe")
        print("2. On first run, Playwright browsers need to be installed.")
        print("   Run: playwright install chromium")
        print("   OR the executable will prompt you on first run")
        print("3. The data folder will be created automatically for seen_jobs.txt")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("\n✗ PyInstaller not found.")
        print("Install it with: pip install pyinstaller")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
