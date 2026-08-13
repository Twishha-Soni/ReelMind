import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from rag.util.config import VIDEO_ANALYSIS_MODEL
from rag.models.video_analysis import VideoAnalysis

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY_VIDEO_ANALYZER"))

_ANALYSIS_PROMPT = """
Watch this video carefully and generate a rich semantic summary.

For the summary, include:
- The main topic or skill being demonstrated or discussed
- Key concepts, tools, techniques, or products mentioned
- The mood and style (tutorial, motivational, funny, aesthetic, etc.)
- Any specific details a person might use to search for this later
  (e.g. "morning routine", "React hooks", "sourdough bread", "chest workout")

Write the summary in plain prose. Be specific and descriptive.
Do not say "this video" — just describe the content directly.

For keywords, extract 5-10 specific searchable terms someone would type to find this later — exact tools, techniques, topics, not vague words.
"""


def analyze_video(video_path: Path) -> VideoAnalysis:
    """
    Upload a video to Gemini File API, wait for processing,
    then generate and return a rich semantic summary.

    This summary is what gets embedded into ChromaDB —
    its quality directly determines search result quality.
    """
    print(f"Uploading {video_path.name} to Gemini File API...")

    uploaded_file = _client.files.upload(
        file=video_path,
        config=types.UploadFileConfig(mime_type="video/mp4")
    )

    print("Waiting for Gemini to process the video...")

    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = _client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name != "ACTIVE":
        raise RuntimeError(
            f"File processing failed. Final state: {uploaded_file.state.name}"
        )
    
    print("Generating semantic summary...")

    response = _client.models.generate_content(
        model=VIDEO_ANALYSIS_MODEL,
        contents=[uploaded_file, _ANALYSIS_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=VideoAnalysis,
        ),
    )

    analysis = VideoAnalysis.model_validate_json(response.text.strip())

    _client.files.delete(name=uploaded_file.name)
    print("File deleted from Gemini servers.")

    return analysis
    