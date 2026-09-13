import os
from dotenv import load_dotenv
from google import genai
from langchain_core.prompts import ChatPromptTemplate # type: ignore
from langchain_core.output_parsers import StrOutputParser # type: ignore
from langchain_google_genai import ChatGoogleGenerativeAI # type: ignore
from rag.retrieve.retriever import RetrievedReel
from rag.util.config import ANSWER_FORMAT_MODEL
from rag.models.llm_response import SearchResponse
from tavily import TavilyClient

tavily_client = TavilyClient()
load_dotenv()


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



# -------------- Web search fallback --------------
_grounding_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY_SEARCH_RESULT_GENERATOR'))

def web_search_fallback(query: str) -> str:
    updated_query = f"Search for Instagram Reels only for: {query}"

    results = tavily_client.search(
        query=updated_query,
        max_results=3,
        time_range="year",
        include_domains=["instagram.com"],
    )

    if not results:
        return "Couldn't find anything relevant, even on the web. Try rephrasing your search query."

    results_block = ""
    for r in results['results']:
        results_block += f"Title: {r['title']}\n{r['content']}\n{r['score']}\nURL: {r['url']}\n\n"

    response = _grounding_client.models.generate_content(
        model=ANSWER_FORMAT_MODEL,
        contents=f"""
The user asked: "{query}"

Here are some web search results:
{results_block}

Give a short, casual, helpful answer and format these as a clean, readable Telegram message.
For each result show:
- A short title or topic 
- The URL on its own line so Telegram renders a preview
- One sentence describing why it matches the query 

No markdown headers. Keep it concise — a few sentences. And at the top add this line compulsory that as 'I don't find anything related to your request in your storage, hence these are some useful links I searched on web.'
""",
    )

    return response.text.strip()