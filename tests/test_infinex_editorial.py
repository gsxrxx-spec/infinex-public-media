#!/usr/bin/env python3
"""Validate INFINEX's one-topic-per-carousel editorial calendar without publishing."""
import importlib.util
import zoneinfo
import sys
from datetime import date,timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
sp=importlib.util.spec_from_file_location("infinex_daily_editorial",Path(__file__).resolve().parents[1]/"scripts"/"infinex_daily.py")
original=zoneinfo.ZoneInfo
try:
    zoneinfo.ZoneInfo=lambda _: timezone.utc
    m=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
finally:
    zoneinfo.ZoneInfo=original

expected={"puertas":"gates","escaleras":"structures","cerramientos":"gates","soldadura":"welding"}
seen=set()
for offset in range(8):
    m.DATE=date(2026,11,19).fromordinal(date(2026,11,19).toordinal()+offset)
    for slot in ("09","17"):
        m.SLOT=slot
        m.SLOT_TIME=slot+":00"
        theme=m.topic_for_slot()
        chosen=m.photo_selection()
        assert len(chosen)==3
        assert {group for group,_ in chosen}=={expected[theme]}
        assert len({str(p["id"]) for _,p in chosen})==3
        caption=m.caption_for(chosen)
        assert "presupuesto sin compromiso" in caption.lower()
        assert "#INFINEX" in caption
        assert "No son obras ejecutadas por INFINEX." in caption
        assert m.DATE.strftime("%d/%m/%Y") in caption
        assert len(caption)<2200
        assert len(set([p["page"] for _,p in chosen]))==3
        seen.add(theme)
        print("EDITORIAL_SLOT_OK",m.DATE,slot,theme,3)
assert seen==set(expected)
print("EDITORIAL_SINGLE_TOPIC_TEST_PASSED",len(seen),"themes",16,"slots")

# The owner deleted the mixed-subject morning post. Never republish it.
import json
rejected=Path(__file__).resolve().parents[1]/"records"/"2026-11-19_09.json"
data=json.loads(rejected.read_text(encoding="utf-8"))
assert data["status"]=="REJECTED_BY_USER" and data["do_not_republish"] is True
m.DATE=date(2026,11,19)
m.SLOT="09"
m.SLOT_TIME="09:00"
m.RECORD_FILE=rejected
m.preflight=lambda: True
m.api=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("Unexpected API call"))
m.publish()
print("EDITORIAL_REJECTED_POST_NO_REPUBLISH_PASSED")
