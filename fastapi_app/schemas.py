"""Pydantic request/response models for the search service."""
from typing import List, Optional

from pydantic import BaseModel, Field


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