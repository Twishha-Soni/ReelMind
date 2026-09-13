<img width="1377" height="207" alt="ChatGPT Image Jun 20, 2026, 11_55_09 AM (1)" src="https://github.com/user-attachments/assets/2922a835-51b2-4c1c-8379-d4e698ab8939" />

# ReelMind

A Telegram bot that turns your saved Instagram reels into a searchable personal library.
Send a reel URL to index it. Type anything in plain English to find it later — by topic, mood, skill, or anything you remember about it.

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-hybrid_vector_store-dc244c?style=flat-square)
![LangChain](https://img.shields.io/badge/LangChain-retrieval-1c3c3c?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5_%2F_3.5_Flash-4285f4?style=flat-square&logo=google&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-MCP_server-6d28d9?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-ready-2496ed?style=flat-square&logo=docker&logoColor=white)

---

## What it does

- **Index by URL** — send any public Instagram reel link and ReelMind downloads it, generates a rich semantic summary via Gemini, and stores it in Qdrant
- **Bulk import** — send your Instagram `saved_posts.json` export and ReelMind indexes every saved reel automatically
- **Hybrid semantic search** — type anything in plain English (`morning routine`, `React hooks tutorial`, `funny cooking fails`) and ReelMind runs combined dense + sparse (BM25) retrieval against your indexed reels
- **LLM-judged web fallback** — if the indexed results genuinely aren't relevant to your query, ReelMind detects this inline and falls back to a live web search instead of showing weak matches
- **No duplicates** — every URL is checked against the index before download; re-sending an already-indexed reel is detected instantly without re-downloading
- **A second client, via MCP** — the same search / stats / ingest capabilities are also exposed as MCP tools, so a client like Claude Desktop can call them directly, outside Telegram entirely

---

## Architecture

<img width="1959" height="939" alt="Workflow_design" src="https://github.com/user-attachments/assets/e872f006-1589-4ca4-96d0-04593b389af7" />


---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Bot interface | `python-telegram-bot` |
| Second client interface | `FastMCP` (MCP server, stdio transport) |
| Video download | `yt-dlp` (silenced via `noprogress` + custom stderr-routed logger) |
| Video understanding | Gemini (File API) via `google-genai` SDK |
| Result formatting + relevance judgment | Gemini via `google-genai` SDK, structured output (`SearchResponse`) |
| Web search fallback | `tavily` + Gemini summarization |
| Embeddings | `sentence-transformers` / HuggingFace (dense) + FastEmbed BM25 (sparse) |
| Vector store | Qdrant — hybrid `RetrievalMode.HYBRID`, dense + sparse collections |
| Retrieval orchestration | LangChain (`QdrantVectorStore`) |
| Duplicate detection | Pre-download index check (`is_already_indexed`) |
| Containerisation | Docker + Docker Compose |

---

## Project structure

```
ReelMind/
├── Dockerfile                     # Container build instructions
├── docker-compose.yml              # Local and production run config
├── .env                            # API keys (never committed)
├── pyproject.toml / uv.lock        # uv-managed dependencies
└── src/
    ├── bot/
    │   ├── telegram_bot.py         # Handler registration and bot startup
    │   └── onboarding.py           # Bulk import from saved_posts.json
    ├── mcp_server/
    │   └── server.py               # FastMCP server — search / stats / ingest as MCP tools
    └── rag/
        ├── util/
        │   └── config.py           # Models, top_k, rate limits
        ├── database/
        │   └── qdrant_setup.py     # Qdrant client, collection setup, hybrid vector store
        ├── ingest/
        │   ├── downloader.py       # yt-dlp wrapper, typed error handling, silent stdout
        │   ├── video_analyzer.py   # Gemini File API — upload, poll, summarize
        │   └── ingestor.py         # Store reel, get_stats, is_already_indexed
        ├── retrieve/
        │   └── retriever.py        # Hybrid Qdrant search, returns RetrievedReel dataclasses
        ├── generate/
        │   └── generator.py        # format_results (+ relevance judge) and web_search_fallback
        └── models/
            ├── llm_response.py      # SearchResponse (formatted_text, needs_web_search)
            └── video_analysis.py
```

---

## MCP server — a second client, outside Telegram

Every ReelMind capability used to be reachable only through the Telegram bot process. The `mcp_server/` package exposes the same underlying `rag/` functions as MCP tools, over stdio, so a separate client (e.g. Claude Desktop) can call them directly:

| Tool | Wraps | Notes |
|---|---|---|
| `search_indexed_reel(query)` | `retriever.search_reel` + `generator.format_results` (+ web fallback) | Same relevance-judged search as the bot, returned as plain text |
| `handle_store_reel(url)` | `downloader.download_reel` → `video_analyzer.analyze_video` → `ingestor.store_reel` | Blocking call — may take up to a minute; errors are returned as messages, not raised, so the client sees a clean result rather than a tool failure |
| `handle_get_stats()` | `ingestor.get_stats` | Total indexed reels, earliest/latest timestamp |

Two mechanical details worth knowing if you extend this:

- **stdio is the wire.** The server's stdout *is* the JSON-RPC channel back to the client — any stray `print()`, or a dependency that writes its own progress output to stdout (yt-dlp's download progress bar was one such case here), corrupts the stream and breaks the connection. All internal logging in this project is routed to `stderr`.
- **Errors are caught and returned, not raised**, for expected failure modes (invalid URL, private reel, deleted reel). Raising would surface as a hard tool-execution failure to the client; returning a message lets the client relay it naturally as information.

To run it standalone for testing (outside any client):

```bash
fastmcp dev src/mcp_server/server.py
```

To register it with Claude Desktop, add an entry to its MCP server config pointing at this repo, e.g.:

```json
{
  "mcpServers": {
    "reelmind": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/ReelMind/src", "python", "-m", "mcp_server.server"]
    }
  }
}
```

---

## Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Gemini API key from [aistudio.google.com](https://aistudio.google.com) (free tier works)
- A tavily APi key from [app.tavily.com](https://app.tavily.com) (free tier works)

---

### 1. Clone the repository

```bash
git clone https://github.com/Twishha-Soni/ReelMind.git
cd ReelMind
```

---

### 2. Create your `.env` file

```bash
cp example.env .env
```

Open `.env` and fill in your keys:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

GEMINI_API_KEY_VIDEO_ANALYZER=your_gemini_api_key1
GEMINI_API_KEY_SEARCH_RESULT_GENERATOR=your_gemini_api_key2

TAVILY_API_KEY=your_tavily_api_key
```

| Key | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram — send `/newbot` |
| `GEMINI_API_KEY_*` | [aistudio.google.com](https://aistudio.google.com) — free tier works |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) - free tier works

> Two separate Gemini keys are used to distribute load across free-tier RPM limits. You can use the same key for both.

Qdrant also needs to be running — the included `docker-compose.yml` starts it alongside the bot. If you're running without Docker (Section 6), start Qdrant separately, e.g. `docker run -p 6333:6333 qdrant/qdrant`.

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

# Stop and remove the container (data is still preserved — it lives in the Qdrant volume)
docker compose down

# Rebuild after a code change and restart
docker compose up --build -d
```

---

### 5. Qdrant persistence locally

Qdrant persists its data to a Docker volume defined in `docker-compose.yml`, so your indexed reels (dense + sparse vectors) survive:

- Container restarts (`docker compose restart`)
- Container removal (`docker compose down` then `docker compose up`)
- Image rebuilds (`docker compose up --build`)

To wipe your local index and start fresh:

```bash
docker compose down -v   # -v also removes the Qdrant volume
docker compose up -d
```

---

### 6. Run without Docker (alternative)

If you prefer running directly with Python (`uv` is used for dependency management):

```bash
uv sync
uv run python src/bot/telegram_bot.py
```

> Make sure Qdrant is reachable at `localhost:6333` (or whatever `QDRANT_HOST`/`QDRANT_PORT` in `rag/database/qdrant_setup.py` point to) before starting the bot.

---

### 7. Running the MCP server

To use ReelMind's capabilities from a second client (e.g. Claude Desktop) instead of Telegram, see [MCP server](#mcp-server--a-second-client-outside-telegram) above.

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

ReelMind runs a hybrid dense + sparse (BM25) search against Qdrant, and returns formatted results with URLs and relative match percentages. If the results genuinely aren't relevant to your query, it falls back to a live web search automatically instead of showing weak matches.

### Commands

| Command | Description |
|---|---|
| `/stats` | Total reels indexed, earliest and latest timestamp |
| `/help` | Usage guide |

---

## Design decisions

**Automatic intent detection** — there are no explicit commands for indexing or searching in the Telegram bot. It detects intent from the message itself: a file triggers bulk import, an Instagram URL triggers ingest, anything else triggers search. This minimises friction on mobile.

**Two Gemini models** — video understanding uses a Gemini Flash model (multimodal, higher capability); result formatting and relevance judgment use a lighter Flash model. Splitting the workload across two models reduces free-tier quota pressure on either one.

**One structured call does formatting *and* relevance judgment** — rather than a separate classifier step, a single Gemini call (`.with_structured_output(SearchResponse)`) both formats Qdrant results into a Telegram-ready message and judges whether they're actually relevant to the query, returning `needs_web_search: bool` alongside the formatted text. If retrieval genuinely missed, the bot falls back to a live web search instead of showing noise.

**Hybrid retrieval over pure dense similarity** — Qdrant stores both dense (semantic) and sparse (BM25 keyword) vectors per reel, combined via LangChain's `RetrievalMode.HYBRID`. This catches matches that pure embedding similarity misses (exact terms, names, acronyms) alongside semantic matches.

**MCP as a second, independent consumer** — rather than only being reachable through the Telegram bot process, core capabilities (search, stats, ingest) are also exposed as MCP tools over stdio via `FastMCP`. The MCP server imports and calls the same `rag/` functions the bot uses — no duplicated logic — so both clients stay in sync automatically.

**Docker-first** — the project is containerised so it runs identically on any machine or server without manual environment setup, and `docker-compose.yml` brings up Qdrant alongside the bot.

**Qdrant over ChromaDB** — the project was rebuilt from an earlier ChromaDB-based version to Qdrant, to support hybrid dense + sparse retrieval and a more production-realistic vector store setup (persistent volume, dedicated collections, no in-process client).
