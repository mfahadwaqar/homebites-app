"""Reviewed, locally bundled photographs; no remote requests during browsing."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def reviewed_photos():
    return json.loads((Path(__file__).parent / "data" / "photo_sources.json").read_text(encoding="utf-8"))


def photo_for_dish(code):
    return reviewed_photos().get(code)
