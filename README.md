<img width="1774" height="248" alt="ChatGPT Image Jun 16, 2026, 10_01_38 AM" src="https://github.com/user-attachments/assets/82bfd071-8a15-4b3e-a64c-0716f52980ed" />

# ReelMind

A Telegram bot that turns your saved Instagram reels into a searchable personal library.
Send a reel URL to index it. Type anything in plain English to find it later — by topic, mood, skill, or anything you remember about it.

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-f97316?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285f4?style=flat-square&logo=google&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-all--MiniLM--L6--v2-8b5cf6?style=flat-square)

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
| Result formatting | Gemini 2.0 Flash Lite via `google-genai` SDK |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector store | ChromaDB (`PersistentClient`, local disk) |
| Duplicate detection | SHA-256 URL hashing |

---

## Project structure

```
ReelMind/
├── .env                      # API keys (never commit this)
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

### 1. Clone and install

```bash
git clone https://github.com/your-username/ReelMind.git
cd ReelMind
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create your `.env` file

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

GEMINI_API_KEY_VIDEO_ANALYZER=your_gemini_api_key
GEMINI_API_KEY_SEARCH_RESULT_GENERATOR=your_gemini_api_key
```

| Key | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram — create a new bot |
| `GEMINI_API_KEY_*` | [aistudio.google.com](https://aistudio.google.com) — free tier works |

> Two separate Gemini keys are used to distribute load across free-tier RPM limits. You can use the same key for both.

### 3. Run the bot

```bash
cd src
python -m bot.telegram_bot
```

The terminal will print `ReelMind bot is running.` Open Telegram and start chatting with your bot.

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

**Two Gemini models** — video understanding uses `gemini-2.5-flash` (multimodal, higher capability); result formatting uses `gemini-2.0-flash-lite` (fast, lightweight). Splitting the workload across two models reduces free-tier quota pressure on either one.

**SHA-256 URL hashing** — URLs are hashed to produce stable, filesystem-safe ChromaDB document IDs. Same URL always maps to the same ID, so `upsert` silently overwrites instead of duplicating — no extra deduplication logic needed.

**Local vector store** — ChromaDB persists to disk at `./chroma_store`. No external database, no cloud dependency, no monthly bill.
