import json
import logging
import time
import uuid
from django.conf import settings
from datetime import datetime, timezone


class RequestLogMiddleware:
    """Log route names and outcomes, never passwords, cookies, bodies, or query strings."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter_ns()
        request.request_id = uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        response["X-Server-Node"] = settings.NODE_NAME
        status = response.status_code
        level = "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO"
        route = request.resolver_match.url_name if request.resolver_match else "unmatched"
        event = {"schema_version": 1, "event_id": request.request_id, "request_id": request.request_id,
                 "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "node": settings.NODE_NAME, "service": "grocery-web", "operation": route or "unnamed",
                 "level": level, "outcome": "failure" if status >= 500 else "rejected" if status >= 400 else "success",
                 "code": f"http_{status}", "duration_us": (time.perf_counter_ns() - start) // 1000}
        logging.getLogger("grocery.events").info(json.dumps(event))
        return response
