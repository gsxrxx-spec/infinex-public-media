#!/usr/bin/env python3
"""Offline integrity/label QA for the before/after Meta publisher. NO publishing."""
from pathlib import Path
from datetime import datetime,date
import json,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import infinex_before_after as worker
from infinex_editorial_policy import topic_from_caption

base=Path(__file__).resolve().parents[1]
for day in (date(2026,11,22),date(2026,11,24),date(2026,11,26)):
    worker.DAY=day;worker.DATE=day.isoformat()
    worker.LEDGER=base/"records"/(worker.DATE+"_09_before_after.json")
    m=worker.manifest()
    cap=worker.caption(m)
    assert topic_from_caption(cap)==m["topic"]
    assert "Simulación digital ilustrativa" in cap
    assert "No corresponde a una instalación real" in cap
    assert m["scene_key"].startswith("pexels:")
    reg=json.loads((base/"assets/before_after/USED_SCENES.json").read_text(encoding="utf-8"))
    if m["scene_key"] not in reg["used_sources"]:
        worker.sources_available(m)
    else:
        assert worker.LEDGER.exists(),("RESERVED_SCENE_MISSING_LEDGER",day)
    assert m["images"][0]["sha256"]!=m["images"][1]["sha256"]
    worker.MODE="dry_run"
    worker.main()
print("INFINEX_BEFORE_AFTER_META_READONLY_QA_PASSED_3_DAYS")
