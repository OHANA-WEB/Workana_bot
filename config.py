"""Load config from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_WEBHOOK_JOBS = os.getenv("DISCORD_WEBHOOK_JOBS", "").strip()
DISCORD_WEBHOOK_BIDS = os.getenv("DISCORD_WEBHOOK_BIDS", "").strip()
DISCORD_WEBHOOK_BIDS_2 = os.getenv("DISCORD_WEBHOOK_BIDS_2", "").strip()

# OpenAI (optional; if set, bid generation uses OpenAI instead of local LLM)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None  # e.g. Azure/custom endpoint
OPENAI_TIMEOUT = max(60, int(os.getenv("OPENAI_TIMEOUT", "120")))  # seconds for bid generation (min 60)

# Local LLM server (used when OPENAI_API_KEY is not set)
LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_TIMEOUT = max(60, int(os.getenv("LLAMA_TIMEOUT", "300")))  # seconds for bid generation (min 60)

# Polling
POLL_INTERVAL = max(60, int(os.getenv("POLL_INTERVAL", "300")))  # seconds between checks (min 60)

# Persistence
DATA_DIR = Path(__file__).resolve().parent / "data"
SEEN_JOBS_FILE = DATA_DIR / "seen_jobs.txt"
