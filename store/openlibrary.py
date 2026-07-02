from __future__ import annotations

from typing import Iterable

import requests


OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
DEFAULT_TIMEOUT = 12
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _candidate_cover_urls(cover_id: str | int | None = None, isbn_values: Iterable[str] = ()) -> list[str]:
    candidates: list[str] = []
    if cover_id:
        candidates.append(f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg")
    for isbn in isbn_values:
        cleaned = (isbn or "").strip()
        if cleaned:
            candidates.append(f"https://covers.openlibrary.org/b/isbn/{cleaned}-L.jpg")
    return candidates


def candidate_cover_urls_from_doc(doc: dict) -> list[str]:
    return _candidate_cover_urls(doc.get("cover_i"), doc.get("isbn", []) or [])


def validate_cover_url(url: str, session: requests.Session, timeout: int = DEFAULT_TIMEOUT) -> bool:
    if not url:
        return False
    try:
        response = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
    except requests.RequestException:
        return False

    with response:
        if response.status_code != 200:
            return False
        content_type = (response.headers.get("Content-Type") or "").lower()
        if not content_type.startswith("image/"):
            return False
        return True


def first_valid_cover_url(urls: Iterable[str], session: requests.Session, timeout: int = DEFAULT_TIMEOUT) -> str:
    for url in urls:
        if validate_cover_url(url, session=session, timeout=timeout):
            return url
    return ""


def search_book_docs(title: str, author: str, session: requests.Session, limit: int = 5) -> list[dict]:
    params = {
        "title": title,
        "author": author,
        "limit": limit,
    }
    response = session.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json().get("docs", [])
