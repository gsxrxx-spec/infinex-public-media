#!/usr/bin/env python3
"""Preflight curated licensed Pexels photos for the two first informative slots."""
from datetime import date
from pathlib import Path
import sys,json
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"scripts"))
import infinex_daily as daily
from infinex_carousel_quality import used_photos
stock=json.loads((BASE/"assets/photo_library.json").read_text(encoding="utf-8"))
used,_,_,_=used_photos(BASE)
pairs=[(date(2026,11,23),"escaleras","structures"),
       (date(2026,11,27),"soldadura","welding")]
seen=set()
for day,topic,group in pairs:
    daily.DATE=day;daily.SLOT="09";daily.EDITORIAL_THEME=None
    assert daily.topic_for_slot()==topic
    picks=daily.photo_candidates(topic)[:3]
    assert len(picks)==3
    ids=[]
    for cat,p in picks:
        assert cat==group and p.get("curated_premium") is True
        assert str(p["id"]) not in used and str(p["id"]) not in seen
        assert p["page"].startswith("https://www.pexels.com/photo/")
        assert p["page"].rstrip("/").endswith("-"+str(p["id"]))
        ids.append(p["id"]);seen.add(str(p["id"]))
    print("INFINEX_CURATED_INFO_SOURCES_READY",day,topic,ids)
assert len(seen)==6
print("INFINEX_2_INFORMATIVE_CAROUSELS_6_FRESH_SOURCES_READY")
