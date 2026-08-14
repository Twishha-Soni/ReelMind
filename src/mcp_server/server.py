from fastmcp import FastMCP
import sys
from rag.retrieve.retriever import search_reel
from rag.generate.generator import format_results, web_search_fallback
from rag.ingest.ingestor import get_stats, is_already_indexed, store_reel
from rag.ingest.downloader import download_reel
from rag.ingest.video_analyzer import analyze_video

mcp = FastMCP('reelmind')


@mcp.tool()
def search_indexed_reel(query: str) -> str:
    """
    Search indexed Instagram reels by meaning and return a readable summary of matches.
    """
    query = query.strip()
    try:
        results = search_reel(query)
        search_response = format_results(query, results)

        if search_response.needs_web_search:
            print('Going for web search...', file=sys.stderr)
            reply = web_search_fallback(query)
        else:
            reply = search_response.formatted_text

        return reply
 
    except Exception as e:
        return f"Something went wrong during search:\n{str(e)}"

@mcp.tool()
def handle_store_reel(url: str) -> str:
    """
    Triggered when the user sends a message containing an Instagram URL.
    Eventually calls the full ingest pipeline.
    """
    if is_already_indexed(url):
        return "This reel is already ingested. You can search for it anytime."

    try:
        # step 1 - donwload
        video_path  = download_reel(url)

        # step 2 - analyze
        analysis = analyze_video(video_path)

        # step 3 - store
        store_reel(url, analysis)

        # step 4 - clean up temp file
        video_path.unlink(missing_ok=True)
        video_path.parent.rmdir()

        return f"Reel ingested successfully.\n {analysis.summary[:70]}..."

    except ValueError as e:
        return f"Invalid URL: {e}"

    except PermissionError as e:
        return f"Can't access this reel: {e}"

    except FileNotFoundError as e:
        return f"Reel not found: {e}"

    except RuntimeError as e:
        return f"Something went wrong: {e}"

    except Exception as e:
        return f"Unexpected error while ingesting. Please try again.\n{str(e)}"

@mcp.tool()
def handle_get_stats() -> str:
    """Return the number of indexed reels and the earliest/latest indexed timestamps."""

    stats = get_stats()

    if stats["total"] == 0:
        return """No  reels indexed yet.\n"
        Send me an Instagram reel URL or you saved_posts.json file to get started."""

    return f"""
ReelMind Stats\n\n
Reels indexed: {stats['total']}\n
Earliest: {stats['earliest']}\n
Latest: {stats['latest']}
"""


if __name__ == "__main__":
    mcp.run()