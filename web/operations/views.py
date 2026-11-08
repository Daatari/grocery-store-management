import json
import sqlite3
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "node": settings.NODE_NAME})


@login_required
@require_GET
def logs(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Only system administrators can review centralized logs.")
    filters = {key: request.GET.get(key, "").strip() for key in ("node", "level", "operation", "since", "request_id")}
    clauses, values = [], []
    error, events, nodes, count = "", [], [], 0
    try:
        if filters["level"] and filters["level"] not in ("INFO", "WARN", "ERROR"):
            raise ValueError("Choose a valid severity.")
        for column in ("node", "level", "operation", "request_id"):
            if filters[column]:
                if len(filters[column]) > 128:
                    raise ValueError("Filter is too long.")
                clauses.append(f"{column} = ?")
                values.append(filters[column])
        if filters["since"]:
            datetime.strptime(filters["since"], "%Y-%m-%dT%H:%M:%SZ")
            clauses.append("timestamp >= ?")
            values.append(filters["since"])
        if not settings.LOG_INDEX_PATH.is_file():
            raise FileNotFoundError
        database = sqlite3.connect(settings.LOG_INDEX_PATH.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        try:
            nodes = [row[0] for row in database.execute("SELECT DISTINCT node FROM events ORDER BY node")]
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            count = database.execute("SELECT COUNT(*) FROM events" + where, values).fetchone()[0]
            events = [json.loads(row[0]) for row in database.execute(
                "SELECT payload FROM events" + where + " ORDER BY timestamp DESC, node, event_id LIMIT 100", values)]
        finally:
            database.close()
    except ValueError:
        error = "Check the filters. Use a UTC timestamp such as 2026-11-08T00:00:00Z."
    except (OSError, sqlite3.Error):
        error = "The log index is not available yet. Check the collector service."
    from orders.models import Order
    return render(request, "operations/logs.html", {"review_orders": Order.objects.filter(status="needs_review"), "events": events, "nodes": nodes, "count": count,
                                                   "filters": filters, "error": error}, status=400 if error else 200)


@login_required
@require_POST
def retry_payment(request, pk):
    from orders.worker import retry_review
    retry_review(request.user, pk)
    return redirect("event-logs")
