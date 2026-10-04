import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured, ValidationError

from catalog.models import COUNTRIES, validate_ingredients


MANIFEST_VERSION = "2026-10-04-v1"


def validate_manifest_document(document):
    if not isinstance(document, dict) or document.get("version") != MANIFEST_VERSION:
        raise ImproperlyConfigured("Catalogue manifest version is unsupported.")
    return validate_manifest(document.get("dishes"))


def validate_manifest(rows):
    if not isinstance(rows, list) or len(rows) != 50:
        raise ImproperlyConfigured("Catalogue manifest must contain exactly 50 dishes.")
    codes = set()
    names = set()
    countries = Counter()
    for row in rows:
        if not isinstance(row, dict) or not {"code", "country", "name", "description", "ingredients", "price"} <= row.keys():
            raise ImproperlyConfigured("Catalogue manifest row is incomplete.")
        code, country, name = row["code"], row["country"], row["name"]
        if (
            not isinstance(code, str)
            or not isinstance(country, str)
            or country not in COUNTRIES
            or len(code) != 4
            or code[:2] != country
            or not code[2:].isdigit()
            or not 1 <= int(code[2:]) <= 10
            or code in codes
        ):
            raise ImproperlyConfigured("Catalogue dish code or country is invalid.")
        if not isinstance(name, str) or not name.strip() or (country, name) in names:
            raise ImproperlyConfigured("Catalogue dish name is invalid or duplicated.")
        if not isinstance(row["description"], str) or not row["description"].strip():
            raise ImproperlyConfigured("Catalogue dish description is required.")
        try:
            validate_ingredients(row["ingredients"])
        except ValidationError as exc:
            raise ImproperlyConfigured("Catalogue dish ingredients are invalid.") from exc
        try:
            price = Decimal(row["price"])
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ImproperlyConfigured("Catalogue offer price is invalid.") from exc
        if not price.is_finite() or price <= 0 or price >= Decimal("10000000") or price.as_tuple().exponent < -2:
            raise ImproperlyConfigured("Catalogue offer price must fit a positive nine-digit, two-decimal field.")
        codes.add(code)
        names.add((country, name))
        countries[country] += 1
    if countries != {code: 10 for code in COUNTRIES}:
        raise ImproperlyConfigured("Catalogue manifest must contain ten dishes for each of five countries.")
    return rows


@lru_cache(maxsize=1)
def load_manifest():
    path = Path(__file__).parent / "data" / "dishes.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    return validate_manifest_document(document)


def dish_index():
    return {row["code"]: row for row in load_manifest()}
