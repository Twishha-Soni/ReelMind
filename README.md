<img width="1377" height="207" alt="ChatGPT Image Jun 20, 2026, 11_55_09 AM (1)" src="https://github.com/user-attachments/assets/2922a835-51b2-4c1c-8379-d4e698ab8939" />

# ReelMind

A Telegram bot that turns your saved Instagram reels into a searchable personal library.
Send a reel URL to index it. Type anything in plain English to find it later — by topic, mood, skill, or anything you remember about it.

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-f97316?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285f4?style=flat-square&logo=google&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-all--MiniLM--L6--v2-8b5cf6?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-ready-2496ed?style=flat-square&logo=docker&logoColor=white)

---

## What it does

- **Index by URL** — send any public Instagram reel link and ReelMind downloads it, generates a rich semantic summary via Gemini, and stores it in a local vector database
- **Bulk import** — send your Instagram `saved_posts.json` export and ReelMind indexes every saved reel automatically
- **Semantic search** — type anything in plain English (`morning routine`, `React hooks tutorial`, `funny cooking fails`) and ReelMind returns the most relevant reels from your collection
- **No duplicates** — every URL is SHA-256 hashed before storage; re-sending an already-indexed reel is detected instantly without re-downloading

---

## Architecture

```
User (Telegram)
      │
      ▼
┌─────────────────────────────────────────────┐
│              bot/telegram_bot.py             │
│                                             │
│  CommandHandler  → /stats, /help            │
│  MessageHandler  → URL ingest               │
│  MessageHandler  → JSON bulk upload         │
│  MessageHandler  → search fallback          │
└────┬──────────────────────────┬─────────────┘
     │ ingest path              │ search path
     ▼                          ▼
downloader.py            retriever.py
(yt-dlp)                 (sentence-transformers)
     │                          │
     ▼                          ▼
video_analyzer.py          ChromaDB
(Gemini File API)        (PersistentClient)
     │                          │
     ▼                          ▼
embedder.py              generator.py
(ChromaDB upsert)        (Gemini — format results)
                                │
                                ▼
                         Telegram reply
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Bot interface | `python-telegram-bot` |
| Video download | `yt-dlp` |
| Video understanding | Gemini 2.5 Flash via `google-genai` SDK (File API) |
| Result formatting | Gemini 3.1 Flash Lite via `google-genai` SDK |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector store | ChromaDB (`PersistentClient`, local disk) |
| Duplicate detection | SHA-256 URL hashing |
| Containerisation | Docker + Docker Compose |

---

## Project structure

```
ReelMind/
├── Dockerfile                # Container build instructions
├── docker-compose.yml        # Local and production run config
├── .env                      # API keys (never committed)
├── .dockerignore             # Excludes .env, venv, chroma_store from build
├── requirements.txt
├── chroma_store/             # Auto-created on first ingest
└── src/
    ├── bot/
    │   ├── telegram_bot.py   # Handler registration and bot startup
    │   └── onboarding.py     # Bulk import from saved_posts.json
    └── rag/
        ├── config.py         # All constants — models, chunk sizes, rate limits
        ├── downloader.py     # yt-dlp wrapper with typed error handling
        ├── video_analyzer.py # Gemini File API — upload, poll, summarize, delete
        ├── embedder.py       # Embed summaries and store/retrieve from ChromaDB
        ├── retriever.py      # Cosine similarity search, returns RetrievedReel dataclasses
        └── generator.py      # Gemini formats raw results into clean Telegram messages
```

---

## Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Gemini API key from [aistudio.google.com](https://aistudio.google.com) (free tier works)

---

### 1. Clone the repository

```bash
git clone https://github.com/Twishha-Soni/ReelMind.git
cd ReelMind
```

---

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

GEMINI_API_KEY_VIDEO_ANALYZER=your_gemini_api_key
GEMINI_API_KEY_SEARCH_RESULT_GENERATOR=your_gemini_api_key
```

| Key | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram — send `/newbot` |
| `GEMINI_API_KEY_*` | [aistudio.google.com](https://aistudio.google.com) — free tier works |

> Two separate Gemini keys are used to distribute load across free-tier RPM limits. You can use the same key for both.

---

### 3. Run with Docker (recommended)

This is the recommended way to run ReelMind locally. Docker guarantees identical behaviour across machines — no Python version mismatches, no missing system libraries.

**Build the image and start the bot:**

```bash
docker compose up --build
```

`--build` tells Docker to build the image from your local `Dockerfile` before starting. You only need this flag the first time, or after any code change. The first build takes 5–10 minutes (PyTorch and sentence-transformers are large). Subsequent builds reuse cached layers and finish in seconds.

To run in the background (detached mode):

```bash
docker compose up --build -d
```

**Verify the bot is running:**

```bash
docker ps
# Should show: reelmind   Up X seconds
```

**Read the logs:**

```bash
docker logs reelmind          # all logs so far
docker logs -f reelmind       # follow in real time (Ctrl+C to exit)
```

You should see `ReelMind bot is running.` in the logs.

**Open Telegram and send `/help`** — you should get a response immediately.

---

### 4. Stopping and restarting

```bash
# Stop the container (data is preserved)
docker compose stop

# Start it again
docker compose start

# Stop and remove the container (data is still preserved — it lives in chroma_store/)
docker compose down

# Rebuild after a code change and restart
docker compose up --build -d
```

---

### 5. ChromaDB persistence locally

ChromaDB data is stored in `chroma_store/` at your project root via a bind mount. This directory is created automatically on first ingest. It is excluded from the Docker image (via `.dockerignore`) and from Git (via `.gitignore`), so your indexed reels persist across:

- Container restarts (`docker compose restart`)
- Container removal (`docker compose down` then `docker compose up`)
- Image rebuilds (`docker compose up --build`)

To wipe your local index and start fresh:

```bash
docker compose down
rm -rf chroma_store/
docker compose up -d
```

---

### 6. Run without Docker (alternative)

If you prefer running directly with Python:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python3 src/bot/telegram_bot.py
```

> **Note:** This requires Python 3.11+, gcc, and g++ installed on your machine for sentence-transformers to compile. Docker handles all of this automatically.

---

## Usage

### Index a single reel

Send any public Instagram reel URL directly in the chat:

```
https://www.instagram.com/reel/abc123/
```

ReelMind downloads it, analyzes it with Gemini, and confirms when it's indexed.

### Bulk import from Instagram export

1. Go to Instagram → Settings → Your activity → Download your information
2. Request your data in JSON format
3. Once downloaded, find `saved_posts.json` inside the export
4. Send that file directly to the bot

ReelMind will parse every saved reel URL and index them one by one, with progress updates every 10 reels.

### Search your collection

Type anything in plain English:

```
sourdough bread tutorial
chest workout no equipment
React useState explained
funny airport fails
```

ReelMind embeds your query, finds the most semantically similar reels in ChromaDB, and returns formatted results with URLs and match percentages.

### Commands

| Command | Description |
|---|---|
| `/stats` | Total reels indexed, earliest and latest timestamp |
| `/help` | Usage guide |

---

## Design decisions

**Automatic intent detection** — there are no explicit commands for indexing or searching. The bot detects intent from the message itself: a file triggers bulk import, an Instagram URL triggers ingest, anything else triggers search. This minimises friction on mobile.

**Two Gemini models** — video understanding uses `gemini-2.5-flash` (multimodal, higher capability); result formatting uses `gemini-3.1-flash-lite` (fast, lightweight). Splitting the workload across two models reduces free-tier quota pressure on either one.

**SHA-256 URL hashing** — URLs are hashed to produce stable, filesystem-safe ChromaDB document IDs. Same URL always maps to the same ID, so `upsert` silently overwrites instead of duplicating — no extra deduplication logic needed.

**Docker-first** — the project is containerised so it runs identically on any machine or server without manual environment setup. The image pins Python 3.11 and all dependencies, eliminating "works on my machine" issues.

**Local vector store** — ChromaDB persists to disk at `./chroma_store` via a bind mount. No external database, no cloud dependency, no monthly bill.
