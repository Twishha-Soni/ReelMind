import tempfile
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

def download_reel(url: str) -> Path:
    """
    Download an Instagram reel to a temporary directory.
    Returns the Path to the downloaded video file.

    yt-dlp handles all the platform-specific complexity —
    authentication headers, CDN redirects, format negotiation.
    We just hand it a URL and an options dict.
    """
    # tempfile.mkdtemp() creates a fresh temporary directory and returns its path.
    # Each download gets its own isolated folder — no filename collisions
    # if two reels happen to have the same ID on different platforms.
    # Think of it like creating a unique staging area per request.
    temp_dir = tempfile.mkdtemp()

    # yt-dlp options dict — this is how you configure the downloader.
    # outtmpl: where to save the file. %(id)s = platform video ID, %(ext)s = extension.
    # format: prefer mp4. yt-dlp will fall back gracefully if mp4 isn't available.
    # quiet + no_warnings: suppress all terminal noise — we handle output ourselves.
    opts = {
        "outtmpl": str(Path(temp_dir) / "%(id)s.%(ext)s"),
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(opts) as ydl:
            # extract_info downloads the video AND returns a dict of metadata.
            # download=True means actually fetch the file (not just inspect the URL).
            info = ydl.extract_info(url, download=True)

            # yt-dlp's info dict contains the final filename under "requested_downloads".
            # This is safer than reconstructing the path from %(id)s + %(ext)s manually,
            # because yt-dlp sometimes adjusts the extension after format negotiation.
            filepath = Path(ydl.prepare_filename(info))
        
    except ExtractorError:
        # yt-dlp couldn't parse the URL at all
        raise ValueError("That doesn't look like a valid Instagram reel URL.")
    
    except DownloadError as e:
        error_msg = str(e).lower()

        # Inspect the message string to classify the cause
        if "login" in error_msg or "authentication" in error_msg:
            raise PermissionError(
                "This reel requires login to download. "
                "Only public reels can be indexed."
            )
        elif "private" in error_msg:
            raise PermissionError(
                "This reel is from a private account and can't be downloaded."
            )
        elif "not found" in error_msg or "deleted" in error_msg:
            raise FileNotFoundError(
                "This reel doesn't exist or has been deleted."
            )
        else:
            # Unknown download failure — re-raise with a clean message
            raise RuntimeError(
                f"Download failed: {str(e)}"
            )

    if not filepath.exists():
        raise FileNotFoundError(f"Download succeeded but file not found at: {filepath}")
    
    return filepath