"""RapidFuzz-based fuzzy matching. No database, no Django, no AI APIs."""
import os
import re
from typing import List

from rapidfuzz import fuzz

from schemas import Item, SearchResult

# Default minimum score (0-100). Override with env var SEARCH_THRESHOLD
# or per request with ?threshold=... on /search.
DEFAULT_THRESHOLD = float(os.getenv("SEARCH_THRESHOLD", "60"))

# Words that carry no search meaning in vague queries like
# "Where is that black cable I use to connect my laptop to the monitor?"
STOPWORDS = {
    "a", "an", "the", "that", "this", "those", "these", "it", "its", "i", "me",
    "my", "mine", "we", "our", "you", "your", "where", "is", "are", "was",
    "were", "did", "do", "does", "put", "keep", "kept", "find", "got", "have",
    "has", "had", "to", "for", "of", "in", "on", "at", "with", "and", "or",
    "use", "used", "using", "can", "cant", "which", "what", "thing", "stuff",
    "one", "some", "any", "from", "by", "be", "so", "about", "usually",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Weight of the better field (name or description) vs. the weaker one.
# 0.8 / 0.2 means a perfect description match alone still scores >= 80.
BEST_WEIGHT = 0.8


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def query_tokens(query: str) -> List[str]:
    tokens = tokenize(query)
    meaningful = [t for t in tokens if t not in STOPWORDS]
    # If the query was *only* stopwords, fall back to the raw tokens.
    return meaningful or tokens


def _token_score(q_token: str, target_tokens: List[str]) -> float:
    """Best similarity of one query word against any word in the target."""
    best = 0.0
    for t in target_tokens:
        score = fuzz.ratio(q_token, t)  # handles misspellings
        if len(q_token) >= 3 and len(t) >= 3:
            # handles partial words: "charg" -> "charger"
            score = max(score, fuzz.partial_ratio(q_token, t) * 0.9)
        best = max(best, score)
    return best


def _field_score(q_tokens: List[str], text: str) -> float:
    """Average best-match of each query word in the text (order-independent)."""
    target = tokenize(text)
    if not q_tokens or not target:
        return 0.0
    return sum(_token_score(q, target) for q in q_tokens) / len(q_tokens)


def score_item(q_tokens: List[str], item: Item) -> float:
    name_score = _field_score(q_tokens, item.name)
    desc_score = _field_score(q_tokens, item.description or "")
    high, low = max(name_score, desc_score), min(name_score, desc_score)
    return BEST_WEIGHT * high + (1 - BEST_WEIGHT) * low


def search_items(query: str, items: List[Item],
                 threshold: float = DEFAULT_THRESHOLD) -> List[SearchResult]:
    q_tokens = query_tokens(query)
    if not q_tokens or not items:
        return []

    results = []
    for item in items:
        score = score_item(q_tokens, item)
        if score >= threshold:
            results.append(SearchResult(id=item.id, score=round(score, 1)))

    results.sort(key=lambda r: r.score, reverse=True)
    return results