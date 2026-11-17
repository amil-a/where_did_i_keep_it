# Where Did I Keep It? — Django app

Household item memory app. Django owns the SQLite database; the FastAPI search
service (separate project, port 8001) never touches it.

## Run it

```bash
cd django_app
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver        # http://127.0.0.1:8000
```

Start the FastAPI service separately on `http://127.0.0.1:8001`. Without it,
everything works except Search, which shows a friendly error.

## Pages

| URL | Name | Purpose |
|---|---|---|
| `/` | `dashboard` | Counts, quick search, recent items |
| `/items/` | `item_list` | Browse, keyword/category filter, pagination |
| `/items/add/` | `item_create` | Add item |
| `/items/<id>/` | `item_detail` | Item details |
| `/items/<id>/edit/` | `item_update` | Edit |
| `/items/<id>/delete/` | `item_delete` | Delete (POST confirm) |
| `/search/?query=...` | `search` | Calls FastAPI |

## FastAPI contract (what Django sends and expects)

POST `http://127.0.0.1:8001/search`

```json
{"query": "...", "items": [{"id": 1, "name": "...", "description": "..."}]}
```

Expected: `{"results": [{"id": 1, "score": 86.5}]}` — score is 0–100, higher is better.
Django sorts by score, ignores unknown IDs, and handles: service down, timeout,
HTTP error, invalid JSON, wrong response shape.

URL and timeout are in `config/settings.py` (`FASTAPI_SEARCH_URL`, `FASTAPI_TIMEOUT_SECONDS`).

## Known limits (deliberate, for the 4-hour MVP)

- Every search sends all items to FastAPI. Fine for hundreds of items; revisit past a few thousand.
- No authentication: anyone who can reach the server can edit data.
- Location is one free-text field; the "→" separator is only used to render a breadcrumb.
