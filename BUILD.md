# Building the Workana Bot Executable

## Quick Build

### Option 1: Using the batch file (Windows)
```batch
build_exe.bat
```

### Option 2: Manual build
```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
python build_exe.py
```

## Output

The executable will be created in the `dist` folder:
- `dist/workana_bot.exe`

## Setup After Building

1. **Copy the .env file** to the same folder as `workana_bot.exe`
   - The executable needs your Discord webhook URLs and other configuration

2. **Install Playwright browsers** (required for web scraping)
   ```bash
   # Option A: Run the executable with install flag
   workana_bot.exe --install-browsers
   
   # Option B: Install manually
   playwright install chromium
   ```

3. **Run the bot**
   ```bash
   workana_bot.exe
   ```

## File Structure After Build

```
workana_bot/
├── dist/
│   └── workana_bot.exe      # The executable
├── build/                    # Build artifacts (can be deleted)
├── workana_bot.spec          # PyInstaller spec file
└── .env                      # Copy this to dist/ folder
```

## Troubleshooting

### "Playwright browsers not found"
- Run: `playwright install chromium` in your Python environment
- Or use: `workana_bot.exe --install-browsers` (if implemented)

### "Module not found" errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Rebuild the executable

### Large file size
- The executable includes Python runtime and all dependencies
- Playwright browsers are NOT included (installed separately)
- Typical size: 20-50 MB

## Notes

- The executable is standalone - no Python installation needed on the target machine
- Playwright browsers must be installed separately (they're large and platform-specific)
- The `.env` file must be in the same folder as the executable
- The `data` folder will be created automatically for storing `seen_jobs.txt`
