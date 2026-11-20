import json
from typing import Optional
from urllib.request import urlopen


def checksum_valid(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
    return (10 - total % 10) % 10 == int(isbn[12])


def remote_title(isbn: str, timeout: float = 5.0) -> Optional[str]:
    """Looks the title up in the Open Library registry (not called by the tests)."""
    with urlopen(f'https://openlibrary.org/isbn/{isbn}.json', timeout=timeout) as response:  # noqa: S310
        return json.load(response).get('title')
