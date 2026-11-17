import requests
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ItemForm, SearchForm
from .models import Item


def dashboard(request):
    recent_items = Item.objects.all()[:5]
    context = {
        "total_items": Item.objects.count(),
        "category_count": Item.objects.values("category").distinct().count(),
        "recent_items": recent_items,
    }
    return render(request, "inventory/dashboard.html", context)


def item_list(request):
    items = Item.objects.all()
    category = request.GET.get("category", "").strip()
    text = request.GET.get("q", "").strip()

    if category:
        items = items.filter(category__iexact=category)
    if text:
        # Simple keyword filter for browsing. The smart search lives on the Search page.
        items = items.filter(
            Q(name__icontains=text) | Q(description__icontains=text) | Q(location__icontains=text)
        )

    paginator = Paginator(items, 12)
    page = paginator.get_page(request.GET.get("page"))
    categories = (
        Item.objects.order_by("category").values_list("category", flat=True).distinct()
    )
    return render(
        request,
        "inventory/item_list.html",
        {
            "page": page,
            "categories": categories,
            "selected_category": category,
            "q": text,
        },
    )


def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    location_parts = [p.strip() for p in item.location.split("→") if p.strip()]
    return render(
        request,
        "inventory/item_detail.html",
        {"item": item, "location_parts": location_parts},
    )


def _category_options():
    return Item.objects.order_by("category").values_list("category", flat=True).distinct()


def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"Saved “{item.name}”.")
            return redirect("item_detail", pk=item.pk)
    else:
        form = ItemForm()
    return render(
        request,
        "inventory/item_form.html",
        {"form": form, "title": "Add item", "categories": _category_options()},
    )


def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated “{item.name}”.")
            return redirect("item_detail", pk=item.pk)
    else:
        form = ItemForm(instance=item)
    return render(
        request,
        "inventory/item_form.html",
        {
            "form": form,
            "title": f"Edit {item.name}",
            "item": item,
            "categories": _category_options(),
        },
    )


def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        name = item.name
        item.delete()
        messages.success(request, f"Deleted “{name}”.")
        return redirect("item_list")
    return render(request, "inventory/item_confirm_delete.html", {"item": item})


def _call_fastapi(query, items):
    """
    Send the query and all items to the FastAPI search service.

    Returns (results, error_message). Exactly one of them is None.
    results is a list of {"id": int, "score": float}.
    """
    payload = {
        "query": query,
        "items": [
            {"id": i.id, "name": i.name, "description": i.description} for i in items
        ],
    }
    try:
        response = requests.post(
            settings.FASTAPI_SEARCH_URL,
            json=payload,
            timeout=settings.FASTAPI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        raw_results = data["results"]
        results = [
            {"id": int(r["id"]), "score": float(r["score"])} for r in raw_results
        ]
    except requests.exceptions.ConnectionError:
        return None, (
            "The search service is not running. Start the FastAPI service on "
            "http://127.0.0.1:8001 and try again."
        )
    except requests.exceptions.Timeout:
        return None, "The search service took too long to respond. Please try again."
    except requests.exceptions.HTTPError as exc:
        return None, f"The search service returned an error ({exc.response.status_code})."
    except (ValueError, KeyError, TypeError):
        # ValueError covers invalid JSON; KeyError/TypeError cover a wrong response shape.
        return None, "The search service sent a response in an unexpected format."
    except requests.exceptions.RequestException:
        return None, "Could not reach the search service."
    return results, None


def search(request):
    form = SearchForm(request.GET or None)
    matches = []
    error = None
    searched = False

    if form.is_bound and form.is_valid():
        searched = True
        query = form.cleaned_data["query"].strip()
        items = list(Item.objects.all())

        if items:
            results, error = _call_fastapi(query, items)
            if results is not None:
                # Django is the only app that reads the database: look up real records by ID.
                items_by_id = {item.id: item for item in items}
                for r in sorted(results, key=lambda r: r["score"], reverse=True):
                    item = items_by_id.get(r["id"])
                    if item is not None:  # ignore unknown IDs instead of crashing
                        matches.append({"item": item, "score": round(r["score"], 1)})

    return render(
        request,
        "inventory/search.html",
        {
            "form": form,
            "matches": matches,
            "error": error,
            "searched": searched,
            "has_items": Item.objects.exists(),
        },
    )
