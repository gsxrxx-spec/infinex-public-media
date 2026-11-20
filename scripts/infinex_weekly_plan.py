#!/usr/bin/env python3
"""INFINEX two Instagram windows daily: 12 carousels and 2 Reels weekly."""
from __future__ import annotations
from datetime import date, datetime, time as dtime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
START_DATE = date(2026, 11, 21)
WEEKLY_PLAN: dict[int, tuple[tuple[str, str], ...]] = {
    0: (("09", "reel"), ("17", "carousel")),
    1: (("09", "carousel"), ("17", "carousel")),
    2: (("09", "carousel"), ("17", "carousel")),
    3: (("09", "carousel"), ("17", "reel")),
    4: (("09", "carousel"), ("17", "carousel")),
    5: (("09", "carousel"), ("17", "carousel")),
    6: (("09", "carousel"), ("17", "carousel")),
}
TRANSITION_EXCEPTIONS = {
    date(2026, 11, 21): (("09", "reel"), ("17", "carousel")),
}

def scheduled_posts(day: date) -> tuple[tuple[str, str], ...]:
    if not isinstance(day, date) or day < START_DATE:
        return ()
    return TRANSITION_EXCEPTIONS.get(day, WEEKLY_PLAN[day.weekday()])

def scheduled_post(day: date) -> tuple[str, str] | None:
    """Backward-compatible first slot; use scheduled_posts for both slots."""
    return next(iter(scheduled_posts(day)), None)

def is_scheduled(day: date, slot: str, kind: str) -> bool:
    return (slot, kind) in scheduled_posts(day)

def due(day: date, slot: str, kind: str, now: datetime | None = None) -> bool:
    if not is_scheduled(day, slot, kind):
        return False
    now = (now or datetime.now(TZ)).astimezone(TZ)
    return now.date() > day or (
        now.date() == day and now.time() >= dtime(hour=int(slot))
    )
