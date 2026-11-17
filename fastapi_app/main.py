"""FastAPI service for "Where Did I Keep It?": fuzzy search + voice-transcript extraction."""
from typing import Optional

from fastapi import FastAPI, Query

from extractor import extract_item
from schemas import ExtractRequest, ExtractResponse, SearchRequest, SearchResponse
from search_engine import DEFAULT_THRESHOLD, search_items

app = FastAPI(title="Where Did I Keep It? - Search Service", version="1.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "default_threshold": DEFAULT_THRESHOLD}


@app.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    threshold: Optional[float] = Query(
        None, ge=0, le=100,
        description="Optional minimum score (0-100) for this request. "
                    "Defaults to SEARCH_THRESHOLD env var (60).",
    ),
):
    cutoff = DEFAULT_THRESHOLD if threshold is None else threshold
    return SearchResponse(results=search_items(payload.query, payload.items, cutoff))


@app.post("/extract-item", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    """Turn a spoken sentence into name / description / category / location.
    Unknown fields come back as empty strings; nothing is invented."""
    return ExtractResponse(**extract_item(payload.transcript, payload.categories))