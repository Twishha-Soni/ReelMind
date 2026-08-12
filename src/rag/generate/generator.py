import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate # type: ignore
from langchain_core.output_parsers import StrOutputParser # type: ignore
from langchain_google_genai import ChatGoogleGenerativeAI # type: ignore
from rag.retrieve.retriever import RetrievedReel
from rag.util.config import ANSWER_FORMAT_MODEL

load_dotenv()

_llm = ChatGoogleGenerativeAI(
    model=ANSWER_FORMAT_MODEL,
    google_api_key=os.getenv('GEMINI_API_KEY_SEARCH_RESULT_GENERATOR')
)

_prompt = ChatPromptTemplate.from_template("""
You are formatting search results for a Telegram bot called ReelMind.
The user searched for: "{query}"

Here are the matching reels:

{results_block}

Format these as a clean, readable Telegram message.
For each result show:
- A short title or topic (derived from the summary, not copied verbatim)
- The match percentage
- The URL on its own line so Telegram renders a preview
- One sentence describing why it matches the query

Keep the tone casual and helpful. No markdown headers. No bullet walls.
Separate each result with a blank line. Order with higher priority one first.
If the matching reels attached are not at all totally relevant just say "No such content in your collection...".
If there is only one result, still format it the same way.
""")

_chain = _prompt | _llm | StrOutputParser()

def _build_results_block(results: list[RetrievedReel]) -> str:
    results_block = ''
    for i, reel in enumerate(results, start=1):
        results_block += f"""
Result {i}:
URL: {reel.url}
Similarity: {{reel.similarity}}%
Indexed on: {reel.timestamp}
Summary: {reel.summary}
""".strip() + '\n\n'

    return results_block

def format_results(query: str, results: list[RetrievedReel]) -> str:
    if not results:
        return 'No matching reels found. Try a different search.'

    results_block = _build_results_block(results)

    return _chain.invoke({
        'query': query,
        'results_block': results_block
    }).strip()
    