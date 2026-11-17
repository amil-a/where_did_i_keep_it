"""Pydantic request/response models for the search and extraction services."""
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- /search ---------------------------------------------------------------
class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""


class SearchRequest(BaseModel):
    query: str
    items: List[Item] = Field(default_factory=list)


class SearchResult(BaseModel):
    id: int
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


# ---- /extract-item ---------------------------------------------------------
class ExtractRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=1000)
    # Optional: existing categories from Django, so the answer can reuse one.
    categories: List[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    name: str = ""
    description: str = ""
    category: str = ""
    location: str = ""