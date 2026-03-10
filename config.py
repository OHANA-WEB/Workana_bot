"""Load config from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_WEBHOOK_JOBS = os.getenv("DISCORD_WEBHOOK_JOBS", "").strip()
DISCORD_WEBHOOK_BIDS = os.getenv("DISCORD_WEBHOOK_BIDS", "").strip()
DISCORD_WEBHOOK_BIDS_2 = os.getenv("DISCORD_WEBHOOK_BIDS_2", "").strip()

# Local LLM server
LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_TIMEOUT = max(60, int(os.getenv("LLAMA_TIMEOUT", "300")))  # seconds for bid generation (min 60)

# Polling
POLL_INTERVAL = max(60, int(os.getenv("POLL_INTERVAL", "300")))  # seconds between checks (min 60)

# Persistence
DATA_DIR = Path(__file__).resolve().parent / "data"
SEEN_JOBS_FILE = DATA_DIR / "seen_jobs.txt"
