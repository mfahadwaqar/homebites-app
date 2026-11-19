"""Template helpers for the simulated payment screens."""
import hashlib

from django import template
from django.utils.html import format_html, format_html_join

register = template.Library()

SIZE = 25


def _finder(grid, top, left):
    for r in range(7):
        for c in range(7):
            on = r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)
            grid[top + r][left + c] = on
    for i in range(-1, 8):
        for r, c in ((top - 1, left + i), (top + 7, left + i), (top + i, left - 1), (top + i, left + 7)):
            if 0 <= r < SIZE and 0 <= c < SIZE:
                grid[r][c] = False


@register.filter
def mock_qr(reference):
    """Decorative QR-like picture derived from a reference. It encodes nothing and cannot be scanned."""
    digest = hashlib.sha256(str(reference).encode()).digest()
    bits = "".join(f"{b:08b}" for b in digest * 3)
    grid = [[False] * SIZE for _ in range(SIZE)]
    i = 0
    for r in range(SIZE):
        for c in range(SIZE):
            grid[r][c] = bits[i % len(bits)] == "1"
            i += 1
    _finder(grid, 0, 0)
    _finder(grid, 0, SIZE - 7)
    _finder(grid, SIZE - 7, 0)
    cells = [(c, r) for r in range(SIZE) for c in range(SIZE) if grid[r][c]]
    rects = format_html_join("", '<rect x="{}" y="{}" width="1" height="1"/>', cells)
    return format_html(
        '<svg class="mock-qr" viewBox="-2 -2 {0} {0}" role="img" aria-label="Payment QR code">'
        '<rect x="-2" y="-2" width="{0}" height="{0}" fill="#fff"/><g fill="#2e2216">{1}</g></svg>',
        SIZE + 4, rects,
    )
