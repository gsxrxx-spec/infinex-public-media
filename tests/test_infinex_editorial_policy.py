#!/usr/bin/env python3
"""Offline, read-only quality checks for Instagram editorial publishing rules."""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from infinex_editorial_policy import TOPICS, assert_not_consecutive, topic_from_caption

CAPTIONS = [
    ("¿Imaginas tu nueva puerta? #PuertasMetalicas #PuertasAMedida", "puertas"),
    ("Tu escalera adaptada a cada hueco #EscalerasMetalicas", "escaleras"),
    ("Vallas y cerramientos para tu entrada #CerramientosMetalicos", "cerramientos"),
    ("Necesitas soldar o reforzar una pieza #Soldadura", "soldadura"),
    ("Puertas y vallas, estructuras y soldadura", None),
    ("Solo INFINEX sin tema explicito", None),
]
for caption, expected in CAPTIONS:
    result = topic_from_caption(caption)
    assert result == expected, (caption, result, expected)

for topic in TOPICS:
    # Same subject in the last real media must be rejected.
    matching = next(x for x, t in CAPTIONS if t == topic)
    try:
        assert_not_consecutive([{"id": "123", "caption": matching}], topic)
        raise AssertionError("SAME_TOPIC_WAS_ACCEPTED_" + topic)
    except RuntimeError as exc:
        assert str(exc) == "INFINEX_CONSECUTIVE_TOPIC_BLOCKED_" + topic.upper()

assert assert_not_consecutive(
    [{"id": "123", "caption": "Una escalera moderna #EscalerasMetalicas"}], "puertas"
) == "escaleras"
assert assert_not_consecutive([], "puertas") is None
for bad in [None, {}, [{"id": "123", "caption": "INFINEX"}],
            [{"id": "123", "caption": "Vallas y puertas"}]]:
    try:
        assert_not_consecutive(bad, "puertas")
        raise AssertionError("UNCLEAR_LATEST_POST_WAS_ACCEPTED")
    except RuntimeError:
        pass

# Confirm the normal scheduler rotates subjects without adjacent duplicates.
from datetime import date, timezone
import zoneinfo
original = zoneinfo.ZoneInfo
try:
    zoneinfo.ZoneInfo = lambda _name: timezone.utc
    spec = importlib.util.spec_from_file_location("infinex_daily_qatest", SCRIPTS/"infinex_daily.py")
    daily = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daily)
finally:
    zoneinfo.ZoneInfo = original
previous = None
for index in range(20):
    daily.DATE = date.fromordinal(date(2026,11,19).toordinal() + index//2)
    daily.SLOT = "09" if index%2 == 0 else "17"
    theme = daily.topic_for_slot()
    assert theme != previous, (previous, theme)
    previous = theme
assert set(daily.SLIDE_DETAILS) == set(TOPICS)
for theme, slides in daily.SLIDE_DETAILS.items():
    assert len(slides) == 3
    for details in slides:
        assert len(details) == 2
        assert all(isinstance(d, str) and 18 <= len(d) <= 63 for d in details)
        assert details[0] != details[1]
print("EDITORIAL_POLICY_TESTS_PASSED")
