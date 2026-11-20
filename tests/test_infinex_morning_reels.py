#!/usr/bin/env python3
"""Offline guardrails: 12 carousels + 2 Reels, every day at 09 and 17."""
import ast,hashlib,json,sys
from datetime import date,timedelta,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
from infinex_editorial_policy import topic_from_caption
from infinex_weekly_plan import scheduled_posts,is_scheduled,due
from infinex_reel_uniqueness import validate_unique,caption_reusable_media_item

tree=ast.parse((root/"scripts/infinex_reel_morning.py").read_text(encoding="utf-8"))
assignment=next(x for x in tree.body if isinstance(x,ast.Assign) and any(
    isinstance(t,ast.Name) and t.id=="CAPTIONS" for t in x.targets))
captions=ast.literal_eval(assignment.value)
for topic,body in captions.items():
    assert topic_from_caption(body)==topic

madrid=ZoneInfo("Europe/Madrid")
week_start=date(2026,11,23)
week=[scheduled_posts(week_start+timedelta(days=i)) for i in range(7)]
assert all(len(day)==2 for day in week)
assert all(day[0][0]=="09" and day[1][0]=="17" for day in week)
assert sum(kind=="carousel" for day in week for _,kind in day)==12
assert sum(kind=="reel" for day in week for _,kind in day)==2
assert scheduled_posts(date(2026,11,21)) == (("09","reel"),("17","carousel"))
assert scheduled_posts(date(2026,11,22)) == (("09","carousel"),("17","carousel"))
assert not is_scheduled(date(2026,11,23),"09","carousel")
assert is_scheduled(date(2026,11,23),"17","carousel")
assert is_scheduled(date(2026,11,26),"17","reel")
assert is_scheduled(date(2026,11,26),"09","carousel")
assert not due(date(2026,11,23),"09","reel",datetime(2026,11,23,8,59,tzinfo=madrid))
assert due(date(2026,11,23),"09","reel",datetime(2026,11,23,9,1,tzinfo=madrid))
assert not due(date(2026,11,26),"17","reel",datetime(2026,11,26,16,59,tzinfo=madrid))
print("WEEKLY_12_CAROUSELS_2_REELS_14_SLOTS_OK")

items=[
    ("2026-11-20","09","escaleras",True),
    ("2026-11-21","09","puertas",True),
    ("2026-11-22","09","cerramientos",False),
    ("2026-11-23","09","puertas",True),
    ("2026-11-26","17","cerramientos",True),
]
blocked=json.loads((root/"assets/reels/NEVER_REUSE.json").read_text(encoding="utf-8"))
known_used={(x["video_sha256"],x["source_video_sha256"]) for x in blocked["used"]}
assert any(x.get("date")=="2026-11-20" and x.get("media_id")=="17915556330484501"
           for x in blocked["used"])
seen_hash=set()
seen_original=set()
seen_caption=set()
for day,slot,topic,enabled in items:
    manifest_file=root/"assets/reels"/(day+"_"+slot+"_"+topic)/"sources.json"
    m=json.loads(manifest_file.read_text(encoding="utf-8"))
    video=root/m["video"]
    assert m["date"]==day and m["topic"]==topic and m["slot"]==slot
    assert m["type"]=="REELS" and m["approved_for_publish"] is enabled
    assert m["illustrative_ai"] is True
    assert video.is_file() and video.stat().st_size>200000
    assert hashlib.sha256(video.read_bytes()).hexdigest()==m["video_sha256"]
    assert len(m["source_video_sha256"])==64
    if not enabled:continue
    if day>="2026-11-21":
        assert len(m.get("caption_hook",""))>=18
        assert topic_from_caption(m["caption_hook"]+"\n"+captions[topic])==topic
        assert m["caption_hook"] not in seen_caption
        seen_caption.add(m["caption_hook"])
        assert is_scheduled(date.fromisoformat(day),slot,"reel")
    assert m["video_sha256"] not in seen_hash, "DUPLICATE_RENDERED_VIDEO"
    assert m["source_video_sha256"] not in seen_original,"DUPLICATE_SOURCE"
    seen_hash.add(m["video_sha256"])
    seen_original.add(m["source_video_sha256"])

# Prove that a published clip is permanently blocked, even with new caption,
# different date and a re-rendered video hash based on the same original.
old=next(x for x in blocked["used"] if x["date"]=="2026-11-20")
test={"video_sha256":"1"*64,"source_video_sha256":old["source_video_sha256"]}
try:
    validate_unique(root,test,"2026-12-15","09")
    raise AssertionError("REUSED_ORIGINAL_WAS_NOT_BLOCKED")
except RuntimeError as e:
    assert "ALREADY_USED" in str(e)
# Verify that exact captions of older Reels cannot masquerade as today's upload.
caption="Un acceso más bonito, diseños de puertas metálicas"
for previous_day in ("2026-11-20T09:17:43+0000",):
    try:
        caption_reusable_media_item({"caption":caption,"timestamp":previous_day},caption,"2026-11-23")
        raise AssertionError("OLD_CAPTION_ACCEPTED")
    except RuntimeError as e:
        assert "CAPTION_REUSED_ANOTHER_DAY" in str(e)
assert caption_reusable_media_item({"caption":caption,"timestamp":"2026-11-23T08:05:00+0000"},caption,"2026-11-23")
print("REEL_UNIQUENESS_PREVIOUSLY_UPLOADED_VIDEO_BLOCKED")
print("REEL_QUEUED_CONTENT_VALIDATED",len(seen_hash))
