#!/usr/bin/env python3
"""INFINEX before-after review: permanent reject, replacement approved, upcoming pending."""
from pathlib import Path
from datetime import date
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import infinex_before_after as worker
from infinex_gate_geometry_qa import validate_fit
from PIL import Image
base=Path(__file__).resolve().parents[1]
worker.DAY=date(2026,11,22);worker.DATE="2026-11-22"
worker.LEDGER=base/"records/2026-11-22_09_before_after.json"
prior=json.loads(worker.LEDGER.read_text(encoding="utf-8"))
assert prior["status"]=="REJECTED_BY_USER" and prior["do_not_republish"] is True
assert prior["media_id"]=="17956845819279745"
old=json.loads(next((base/"assets/before_after").glob("2026-11-22_09_*/sources.json")).read_text(encoding="utf-8"))
assert old["approved_for_publish"] is False
worker.MODE="dry_run";worker.main()
print("INFINEX_USER_REJECTED_GATE_NEVER_REPOST_OK")

worker.DAY=date(2026,11,24);worker.DATE="2026-11-24"
worker.LEDGER=base/"records/2026-11-24_09_before_after.json"
candidates=[json.loads(x.read_text(encoding="utf-8-sig"))
            for x in (base/"assets/before_after").glob("2026-11-24_09_*/sources.json")]
assert len(candidates)==2
approved=[m for m in candidates if m["approved_for_publish"]]
assert len(approved)==1 and approved[0]["scene_key"]=="pexels:37164155"
assert any(not m["approved_for_publish"] for m in candidates)
m=worker.manifest()
assert m["physical_installation_fit"]["final_render_visual_review"]["status"]=="PASS"
with Image.open(base/m["source_image"]) as im:
    assert validate_fit(m["physical_installation_fit"],im.size,True)
assert worker.sources_available(m).get("schema")==1
worker.main()
print("INFINEX_NEW_GATE_REPLACEMENT_VERIFIED_AND_APPROVED_FOR_TODAY")

worker.DAY=date(2026,11,26);worker.DATE="2026-11-26"
worker.LEDGER=base/"records/2026-11-26_09_before_after.json"
future=json.loads(next((base/"assets/before_after").glob("2026-11-26_09_*/sources.json")).read_text(encoding="utf-8-sig"))
assert future["approved_for_publish"] is False
try:
    worker.manifest()
    raise AssertionError("UNREVIEWED_THURSDAY_GATE_APPROVED")
except RuntimeError as e:
    assert "ONE_APPROVED_REPLACEMENT_REQUIRED" in str(e)
print("INFINEX_THURSDAY_SCENE_PENDING_NEW_FIT_REVIEW")
