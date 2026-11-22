#!/usr/bin/env python3
"""Safety QA for the post-user-rejected INFINEX before/after queue. No Meta calls."""
from pathlib import Path
from datetime import date
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import infinex_before_after as worker
from infinex_editorial_policy import topic_from_caption
base=Path(__file__).resolve().parents[1]
# User expressly rejected original 22nd gate; must survive manual Instagram deletion.
worker.DAY=date(2026,11,22)
worker.DATE="2026-11-22"
worker.LEDGER=base/"records/2026-11-22_09_before_after.json"
prior=json.loads(worker.LEDGER.read_text(encoding="utf-8"))
assert prior["status"]=="REJECTED_BY_USER" and prior["do_not_republish"] is True
assert prior["media_id"]=="17956845819279745"
old=list((base/"assets/before_after").glob("2026-11-22_09_*/sources.json"))
assert len(old)==1
old_manifest=json.loads(old[0].read_text(encoding="utf-8-sig"))
assert old_manifest["approved_for_publish"] is False
worker.MODE="dry_run"
worker.main()
print("INFINEX_REJECTED_PUBLICATION_NEVER_REPOST_TEST_OK")

# Upcoming gate photos are not approved until anchored to visible structural
# supports and a reviewer signs off on the precise finished render SHA.
for day in ("2026-11-24","2026-11-26"):
    worker.DAY=date.fromisoformat(day)
    worker.DATE=day
    worker.LEDGER=base/"records"/(day+"_09_before_after.json")
    files=list((base/"assets/before_after").glob(day+"_09_*/sources.json"))
    assert len(files)==1
    m=json.loads(files[0].read_text(encoding="utf-8-sig"))
    assert m["approved_for_publish"] is False
    assert m["visual_fit_status"]=="NEEDS_NEW_TWO_SUPPORT_SITE_AND_VISUAL_QA"
    try:
        worker.manifest()
        raise AssertionError("UNVERIFIED_GATE_MANIFEST_DID_NOT_FAIL")
    except RuntimeError as err:
        assert "NOT_APPROVED" in str(err) or "FIT_REVIEW" in str(err)
    print("INFINEX_FUTURE_SCENE_MUST_BE_REPLACED_AND_QA_REVIEWED",day)
print("INFINEX_BEFORE_AFTER_FAIL_SAFE_TESTS_PASSED")
