from pydantic import BaseModel, Field

class SearchResponse(BaseModel):
    formatted_text: str = Field(description="The Telegram-ready formatted message for the matching reels")
    needs_web_search: bool = Field(description="True if the provided reels are not genuinely relevant to the query and a web search should be done instead")