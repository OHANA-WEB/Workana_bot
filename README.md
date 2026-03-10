# Workana → Discord + LLM Bids

Monitor [Workana IT & Programming jobs](https://www.workana.com/jobs?category=it-programming&language=xx), post new jobs to one Discord webhook, then generate bids with your **local llama-server** and post them to a second Discord webhook.

## Setup

1. **Create a virtual environment (recommended)**

   ```powershell
   cd D:\Llama\workana_bot
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**

   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Configure Discord webhooks**

   - In your Discord server: Server Settings → Integrations → Webhooks → New Webhook.
   - Create two webhooks: one for **new jobs**, one for **bids**.
   - Copy `.env.example` to `.env` and set:

   ```env
   DISCORD_WEBHOOK_JOBS=https://discord.com/api/webhooks/XXXX/YYYY
   DISCORD_WEBHOOK_BIDS=https://discord.com/api/webhooks/XXXX/YYYY
   ```

   Optionally set `LLAMA_SERVER_URL` (default `http://127.0.0.1:8080`) and `POLL_INTERVAL` (default 300 seconds).

4. **Run llama-server** (in another terminal)

   ```powershell
   D:\Llama\llama.cpp\build\bin\Release\llama-server.exe -m D:\Llama\llama.cpp\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf -c 4096 --port 8080
   ```

## Usage

### Post new jobs to Discord (one run)

```powershell
python main.py
```

### Run the monitor in a loop (e.g. every 5 minutes)

```powershell
python main.py --loop
```

### Generate a bid for a job and post to Discord

When you see a job you like (e.g. from Discord), run:

```powershell
python main.py --bid "Python developer for API" "https://www.workana.com/jobs/argentina/python-api-project"
```

Optional extra description:

```powershell
python main.py --bid "Python developer" "https://www.workana.com/jobs/..." --bid-desc "Need REST API and PostgreSQL. 2 weeks."
```

- The script calls your local **llama-server** to generate a professional bid.
- The bid is then posted to your **bids** Discord webhook so you can copy or refine it before sending on Workana.

## Files

| File | Purpose |
|------|--------|
| `config.py` | Loads `.env` (webhooks, LLAMA_SERVER_URL, POLL_INTERVAL) |
| `workana.py` | Scrapes Workana jobs (Playwright), tracks seen IDs in `data/seen_jobs.txt` |
| `discord_webhook.py` | Posts job embeds and bid embeds to Discord |
| `bid_generator.py` | Calls llama-server `/v1/chat/completions` to generate bids |
| `main.py` | CLI: monitor, loop, or `--bid` for one job |

## Notes

- **Workana** may change their HTML; if scraping stops finding jobs, selectors in `workana.py` may need updating.
- Keep **llama-server** running when you use `--bid`.
- To avoid rate limits or blocking, don’t set `POLL_INTERVAL` too low (e.g. keep it ≥ 300).
