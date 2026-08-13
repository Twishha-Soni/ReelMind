from pydantic import BaseModel, Field

class VideoAnalysis(BaseModel):
    summary: str = Field(description="Rich semantic summary of the video content, in plain prose")
    keywords: list[str] = Field(description="5-10 specific searchable terms: topics, tools, techniques mentioned")