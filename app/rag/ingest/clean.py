"""HTML cleaning + chunking for ingestion.

Dependency-light: a small regex/HTMLParser-based extractor (no bs4 needed) turns
a fetched HTML page into clean text, then a paragraph-aware chunker splits it
into ~token-sized chunks suitable for retrieval.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List

_SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "svg"}
_BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "br", "tr",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.text()
    # Normalize whitespace; keep paragraph breaks.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join([ln for ln in lines if ln])


def chunk_text(text: str, max_chars: int = 700, overlap: int = 80) -> List[str]:
    """Paragraph-aware chunking with light overlap."""
    paras = [p.strip() for p in text.split("\n") if len(p.strip()) > 1]
    chunks: List[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 1 + len(p) <= max_chars:
            buf = buf + " " + p
        else:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = (tail + " " + p).strip() if tail else p
    if buf:
        chunks.append(buf)
    # Drop tiny fragments.
    return [c for c in chunks if len(c) >= 40]
