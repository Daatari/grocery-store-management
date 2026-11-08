"""Catalog plugin boundary: external data never writes inventory directly."""
import json
import math
import re
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import ProviderQuota


def text(value, maximum):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def normalize(raw):
    if not isinstance(raw, dict):
        raise ValidationError("Invalid product record.")
    code = str(raw.get("code", ""))
    name = text(raw.get("product_name"), 100)
    if not re.fullmatch(r"[0-9]{8,14}", code) or not name:
        raise ValidationError("Product has no usable barcode or name.")
    nutrients = {}
    supplied = raw.get("nutriments", {})
    if isinstance(supplied, dict):
        for key in ("energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
                    "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g"):
            value = supplied.get(key)
            if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 10000:
                nutrients[key] = value
    allergens = raw.get("allergens_tags", [])
    if not isinstance(allergens, list):
        allergens = []
    return {"barcode": code, "name": name, "category": text(raw.get("categories"), 80) or "Packaged foods",
        "brand": text(raw.get("brands"), 120), "package_quantity": text(raw.get("quantity"), 80),
        "ingredients": text(raw.get("ingredients_text"), 4000),
        "allergens": [text(v, 80) for v in allergens[:30] if isinstance(v, str)], "nutrients": nutrients}


@transaction.atomic
def quota():
    row, _ = ProviderQuota.objects.get_or_create(name="off-search", defaults={"started_at": timezone.now()})
    row = ProviderQuota.objects.select_for_update().get(pk=row.pk)
    if row.started_at <= timezone.now() - timedelta(seconds=60):
        row.started_at, row.count = timezone.now(), 0
    if row.count >= 8:
        raise ValidationError("Search limit reached. Wait one minute and try again.")
    row.count += 1
    row.save()


class OpenFoodFacts:
    name = "openfoodfacts"

    def search(self, query):
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 80:
            raise ValidationError("Search must contain 2–80 characters.")
        quota()  # Shared by both web nodes; do not hold the transaction during HTTP.
        params = urlencode({"search_terms": query.strip(), "search_simple": 1, "action": "process",
            "json": 1, "page_size": 8, "fields": "code,product_name,categories,brands,quantity,ingredients_text,allergens_tags,nutriments"})
        request = Request("https://world.openfoodfacts.org/cgi/search.pl?" + params,
                          headers={"User-Agent": settings.OFF_USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                body = response.read(524289)
            if len(body) > 524288:
                raise ValueError("oversized response")
            data = json.loads(body)
            if not isinstance(data, dict) or not isinstance(data.get("products"), list):
                raise ValueError("invalid shape")
        except (URLError, TimeoutError, ValueError, OSError):
            raise ValidationError("Open Food Facts is unavailable. Try later or add a product manually.") from None
        result = []
        for raw in data["products"][:8]:
            try:
                result.append(normalize(raw))
            except ValidationError:
                continue
        return result


PROVIDERS = {"openfoodfacts": OpenFoodFacts()}
