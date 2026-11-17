# Where Did I Keep It? — FastAPI Search Service

## Run
    cd fastapi_app
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8001

Swagger UI: http://127.0.0.1:8001/docs

## Configure threshold
- Default: 60 (env var `SEARCH_THRESHOLD`, e.g. `SEARCH_THRESHOLD=50 uvicorn main:app --port 8001`)
- Per request (handy in Swagger): `POST /search?threshold=45`

## Quick tests
Automated: `python test_search.py`. In Swagger, use the sample items from the spec with queries:
exact name, description sentence, misspelling, partial word, unrelated word, empty query, empty items.

## Django integration guide
Django owns the data. For each search, Django loads the user's items and POSTs them:

    import requests

    def fuzzy_search(user, query):
        items = [{"id": i.id, "name": i.name, "description": i.description}
                 for i in Item.objects.filter(owner=user)]
        try:
            resp = requests.post("http://127.0.0.1:8001/search",
                                 json={"query": query, "items": items}, timeout=3)
            resp.raise_for_status()
        except requests.RequestException:
            return []          # or show "search unavailable"
        results = resp.json()["results"]            # [{"id": 1, "score": 86.5}, ...]
        by_id = {i.id: i for i in Item.objects.filter(id__in=[r["id"] for r in results])}
        return [(by_id[r["id"]], r["score"]) for r in results if r["id"] in by_id]  # already sorted

Notes: send only id/name/description (location is looked up in Django by id); an empty list means
no match; run Django on 8000 and FastAPI on 8001.