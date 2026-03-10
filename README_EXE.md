# Workana Bot - Executable Version

## ✅ Executable Created Successfully!

The executable has been built and is located at:
```
dist/workana_bot.exe
```

## Quick Start

1. **Copy the .env file** to the `dist` folder (same location as `workana_bot.exe`)
   ```
   dist/
   ├── workana_bot.exe
   └── .env          ← Copy your .env file here
   ```

2. **Install Playwright browsers** (required for web scraping)
   ```bash
   # Option 1: Using Python (if you have it installed)
   playwright install chromium
   
   # Option 2: The executable will try to install browsers automatically on first run
   # If that fails, you'll need Python + Playwright installed
   ```

3. **Run the bot**
   ```bash
   cd dist
   workana_bot.exe
   ```

## Usage

The executable supports all the same command-line arguments as the Python script:

```bash
# Monitor for new jobs (default)
workana_bot.exe

# Monitor with visible browser (for debugging)
workana_bot.exe --no-headless

# Enable debug mode (saves HTML to debug_page.html)
workana_bot.exe --debug

# Generate a bid for a specific job
workana_bot.exe --bid "Job Title" "https://www.workana.com/jobs/..."

# Monitor continuously (loop)
workana_bot.exe --loop
```

## File Structure

```
workana_bot/
├── dist/
│   ├── workana_bot.exe    ← The executable (use this!)
│   └── .env               ← Copy your .env file here
├── data/                  ← Created automatically
│   └── seen_jobs.txt      ← Tracks which jobs were already posted
└── build/                 ← Build artifacts (can be deleted)
```

## Troubleshooting

### "Playwright browsers not found"
- Install browsers: `playwright install chromium`
- Or ensure Python + Playwright is installed on the system

### "Module not found" errors
- Make sure all dependencies are installed
- Rebuild the executable if needed

### ".env file not found"
- Copy your `.env` file to the same folder as `workana_bot.exe`
- The executable looks for `.env` in its current directory

## Rebuilding

To rebuild the executable:
```bash
python build_exe.py
```

Or use the batch file:
```bash
build_exe.bat
```

## Notes

- The executable is standalone - no Python installation needed on the target machine
- Playwright browsers must be installed separately (they're platform-specific and large)
- The `.env` file must be in the same folder as the executable
- The `data` folder will be created automatically
