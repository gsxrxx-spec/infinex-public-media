#!/usr/bin/env python3
"""INFINEX Instagram editorial guards shared by regular and special publishers.

No credentials. Editorial topics are inferred from real public captions using
conservative patterns. If the latest topic cannot be identified, fail closed.
"""
from __future__ import annotations
import re
import unicodedata

TOPICS = ("puertas", "escaleras", "cerramientos", "soldadura")

PATTERNS = {
    "puertas": (r"\bpuertas?\b", r"#puertas?[a-z0-9_]*"),
    "escaleras": (r"\bescaleras?\b", r"#escaleras?[a-z0-9_]*"),
    "cerramientos": (r"\bcerramientos?\b", r"\bvallas?\b",
                       r"#(?:cerramientos?|vallas?)[a-z0-9_]*"),
    "soldadura": (r"\bsoldadura\b", r"\bsoldar\b", r"#soldadura[a-z0-9_]*"),
}

def normalize(value: str) -> str:
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

def topic_from_caption(caption: str) -> str | None:
    content = normalize(caption)
    matches = [
        topic for topic, pats in PATTERNS.items()
        if any(re.search(pat, content) for pat in pats)
    ]
    return matches[0] if len(matches) == 1 else None

def assert_not_consecutive(latest_posts: list, planned_topic: str) -> str | None:
    """Check newest Instagram post against the proposal; never guess unclear topics.

    Must be called after existing-post reconciliation and immediately before
    the irreversible media_publish request. Newest-first Graph /media data.
    """
    if planned_topic not in TOPICS:
        raise RuntimeError("INFINEX_TOPIC_NOT_APPROVED")
    if not isinstance(latest_posts, list):
        raise RuntimeError("INFINEX_RECENT_MEDIA_UNAVAILABLE")
    if not latest_posts:
        return None
    newest = latest_posts[0]
    if not isinstance(newest, dict) or not newest.get("id"):
        raise RuntimeError("INFINEX_RECENT_MEDIA_INVALID")
    previous = topic_from_caption(newest.get("caption", ""))
    if previous is None:
        raise RuntimeError("INFINEX_PREVIOUS_TOPIC_UNCLEAR_REQUIRES_REVIEW")
    if previous == planned_topic:
        raise RuntimeError("INFINEX_CONSECUTIVE_TOPIC_BLOCKED_" + planned_topic.upper())
    return previous
