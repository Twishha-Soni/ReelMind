import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import sys

# Adds the 'src' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.embedder import is_already_indexed, store_reel, get_stats
from rag.downloader import download_reel
from rag.video_analyzer import analyze_video
from rag.retriever import search_reel
from rag.generator import format_results
from bot.onboarding import handle_bulk_onboarding

load_dotenv()

# Handler callbacks

async def handle_reel_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Triggered when the user sends a message containing an Instagram URL.
    Eventually calls the full ingest pipeline — for now, just acknowledges.
    """
    url = update.message.text.strip()

    # Duplicate check — no point re-downloading and re-analyzing
    if is_already_indexed(url):
        await update.message.reply_text(
            f"This reel is already ingested. You can search for it anytime."
        )
        return
    
    # Reply immediately so the user isn't staring at silence
    await update.message.reply_text("Ingesting reel...")

    try:
        # step 1 - donwload
        video_path  = download_reel(url)
        # print("analyzing video...\n")

        # step 2 - analyze
        summary = analyze_video(video_path)
        # print("ingesting summary in chromadb...\n")

        # step 3 - store
        store_reel(url, summary)
        # print("removing video from tmp folder...")

        # step 4 - clean up temp file
        video_path.unlink(missing_ok=True)
        video_path.parent.rmdir()
        # print("messaging user for success of storing...")

        # step 5 - confirm with summary so user sees what was indexed
        await update.message.reply_text(
            f"Reel ingested successfully.\n{summary[:50]}..."
        )

    except ValueError as e:
        await update.message.reply_text(f"Invalid URL: {e}")
    
    except PermissionError as e:
        await update.message.reply_text(f"Can't access this reel: {e}")

    except FileNotFoundError as e:
        await update.message.reply_text(f"Reel not found: {e}")

    except RuntimeError as e:
        await update.message.reply_text(f"Something went wrong: {e}")

    except Exception as e:
        await update.message.reply_text(
            f"Unexpected error while ingesting. Please try again.\n{str(e)}"
        )



async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Receives the Instagram JSON export file, saves it to a temp location, and kicks off bulk onboarding.
    """
    document = update.message.document
    filename = document.file_name

    # Only accept JSON files
    if not filename.endswith(".json"):
        await update.message.reply_text(
            "Please send your saved_posts.json export file."
        )
        return
    
    await update.message.reply_text("Receiving export file...")

    # Download the file from Telegram's servers to a temp path
    tmp_dir = tempfile.mkdtemp()
    json_path = Path(tmp_dir) / filename

    tg_file = await context.bot.get_file(document.file_id)
    await tg_file.download_to_drive(json_path)

    # Hand off to onboarding pipeline
    await handle_bulk_onboarding(json_path, update)

    # Clean up the json file after onboarding finishes
    json_path.unlink(missing_ok=True)
    Path(tmp_dir).rmdir()

    

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Triggered for any text message that isn't an Instagram URL.
    Eventually runs the RAG search pipeline — for now, just echoes the query.
    """
    query = update.message.text.strip()

    try:
        results = search_reel(query)

        if not results:
            await update.message.reply_text(
                f"No matching reels found. Try ingesting some reels first."
            )
            return
        
        reply = format_results(query, results)
        await update.message.reply_text(reply)
    
    except Exception as e:
        await update.message.reply_text(
            f"Something went wrong during search:\n{str(e)}"
        )

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Triggered when user sends /stats.
    Queries ChromaDB for total count and timestamp range, replies with a summary.
    """
    stats = get_stats()

    if stats["total"] == 0:
        await update.message.reply_text(
            "No  reels indexed yet.\n"
            "Send me an Instagram reel URL or you saved_posts.json file to get started."
        )
        return
    
    await update.message.reply_text(
        f"ReelMind Stats\n\n"
        f"Reels indexed: {stats['total']}\n"
        f"Earliest: {stats['earliest']}\n"
        f"Latest:   {stats['latest']}"
    )

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Triggered when user sends /help.
    Explains what ReelMind does and how to use it.
    """
    await update.message.reply_text(
        "*ReelMind* — your personal Instagram reel search engine\n\n"
        "*What it does*\n"
        "Indexes your saved Instagram reels and lets you search them "
        "by meaning — not just keywords.\n\n"
        "*How to use it*\n"
        "1. Send an Instagram reel URL → ReelMind indexes it\n"
        "2. Send your `saved_posts.json` export → bulk index all saved reels\n"
        "3. Type anything in plain English → ReelMind finds the most relevant reels\n\n"
        "*Commands*\n"
        "/stats — how many reels are indexed and when\n"
        "/help — this message",
        parse_mode="Markdown"
    )


# Bot Startup

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
    
    # ApplicationBuilder is the wiring object — analogous to SpringApplication.run()
    app = ApplicationBuilder().token(token).build()

    # Register handlers in priority order — first match wins.
    # filters.Document.ALL matches any file attachment.
    # filters.TEXT matches any plain text message.
    # filters.Regex checks whether the text contains a pattern.
    #
    # Order matters: file check must come before text checks,
    # and URL check must come before the generic search fallback.
    app.add_handler(CommandHandler("stats", handle_stats))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"instagram\.com"), handle_reel_url))
    app.add_handler(MessageHandler(filters.TEXT, handle_search))


    print("ReelMind bot is running. Press CTRL+C to stop.")
    app.run_polling()

if __name__=="__main__":
    main()