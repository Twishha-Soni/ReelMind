import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langchain_core.prompts import ChatPromptTemplate # type: ignore
from langchain_core.output_parsers import StrOutputParser # type: ignore
from langchain_google_genai import ChatGoogleGenerativeAI # type: ignore
from rag.retrieve.retriever import RetrievedReel
from rag.util.config import ANSWER_FORMAT_MODEL
from rag.models.llm_response import SearchResponse

load_dotenv()

_grounding_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY_SEARCH_RESULT_GENERATOR'))

_llm = ChatGoogleGenerativeAI(
    model=ANSWER_FORMAT_MODEL,
    google_api_key=os.getenv('GEMINI_API_KEY_SEARCH_RESULT_GENERATOR')
).with_structured_output(SearchResponse)

_prompt = ChatPromptTemplate.from_template("""
You are formatting search results for a Telegram bot called ReelMind.
The user searched for: "{query}"

Here are the matching reels:

{results_block}

First, judge whether these reels are GENUINELY relevant to the query — not just loosely topic-adjacent. If the user is searching for something specific and these results are noise, weak matches, or a different sub-topic entirely, set needs_web_search to true.

If they are genuinely relevant, set needs_web_search to false and format these as a clean, readable Telegram message.
For each result show:
- A short title or topic (derived from the summary, not copied verbatim)
- The match percentage
- The URL on its own line so Telegram renders a preview
- One sentence describing why it matches the query

Keep the tone casual and helpful. No markdown headers. No bullet walls. Separate each result with a blank line. Order with higher priority one first.

If needs_web_search is true, formatted_text can be a short placeholder like "Searching the web instead...".

If there is only one result, still format it the same way.
""")

_chain = _prompt | _llm

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

def format_results(query: str, results: list[RetrievedReel]) -> SearchResponse:
    if not results:
        return SearchResponse(
            formatted_text='No matching reels found. Try a different search.',
            needs_web_search=True
        )

    results_block = _build_results_block(results)

    return _chain.invoke({
        'query': query,
        'results_block': results_block
    })

def web_search_fallback(query: str) -> str:
    response = _grounding_client.models.generate_content(
        model=ANSWER_FORMAT_MODEL,
        contents=f"""
The user asked: "{query}"

Search the web for at most 3 instagram reels and give a short, casual, helpful answer and format these as a clean, readable Telegram message.
For each result show:
- A short title or topic 
- The URL on its own line so Telegram renders a preview
- One sentence describing why it matches the query 

No markdown headers. Keep it concise — a few sentences. And at the top add this line compulsory that as 'I don't find anything related to your request in your storage, hence these are some useful links I searched on web.'
""",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
    )

    return response.text.strip()