#!/usr/bin/env python3
"""Safety checks for new INFINEX 7-day calendar and forthcoming assets."""
from __future__ import annotations
import json,hashlib,sys
from pathlib import Path
from datetime import date,timedelta,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from infinex_weekly_plan import scheduled_posts,is_scheduled,due,review_due,CHANGE_DATE
from zoneinfo import ZoneInfo

base=Path(__file__).resolve().parents[1]
expected={0:"informative",1:"before_after",2:"reel",3:"before_after",
          4:"informative",5:"reel",6:"before_after"}
madrid=ZoneInfo("Europe/Madrid")
first=date(2026,11,23)
week=[(first+timedelta(days=i),scheduled_posts(first+timedelta(days=i))) for i in range(7)]
assert all(len(posts)==1 and posts[0]==("09",expected[day.weekday()]) for day,posts in week)
assert sum(posts[0][1]=="informative" for _,posts in week)==2
assert sum(posts[0][1]=="before_after" for _,posts in week)==3
assert sum(posts[0][1]=="reel" for _,posts in week)==2
assert scheduled_posts(date(2026,11,21)) == (("09","reel"),("17","carousel"))
assert scheduled_posts(date(2026,11,22)) == (("09","before_after"),)
assert not is_scheduled(date(2026,11,22),"17","carousel")
assert not due(date(2026,11,22),"09","before_after",datetime(2026,11,22,9,29,tzinfo=madrid))
assert due(date(2026,11,22),"09","before_after",datetime(2026,11,22,9,30,tzinfo=madrid))
assert not review_due(date(2026,11,22),"09","before_after",datetime(2026,11,22,9,44,tzinfo=madrid))
assert review_due(date(2026,11,22),"09","before_after",datetime(2026,11,22,9,45,tzinfo=madrid))
print("INFINEX_7_DAILY_0930_0945_2REEL_3BEFOREAFTER_2INFO_OK")

used=json.loads((base/"assets/before_after/USED_SCENES.json").read_text(encoding="utf-8"))
assert used["schema"]==1 and isinstance(used["used_sources"],list)
scene_ids=set()
for day in ("2026-11-22","2026-11-24","2026-11-26"):
    candidate_files=list((base/"assets/before_after").glob(day+"_09_*/sources.json"))
    assert candidate_files
    manifests=[json.loads(f.read_text(encoding="utf-8-sig")) for f in candidate_files]
    approved=[m for m in manifests if m.get("approved_for_publish")]
    if day=="2026-11-24":
        assert len(approved)==1 and approved[0]["scene_key"]=="pexels:37164155"
        assert len(candidate_files)==2
    else:
        assert not approved
    for m in manifests:
        assert m["date"]==day and m["slot"]=="09" and m["time_local"]=="09:30"
        assert m["type"]=="BEFORE_AFTER"
        assert m["illustrative_simulation"] and m["not_actual_infinex_works"]
        assert m["source_license"]=="https://www.pexels.com/license/"
        assert len(m["images"])==2 and len(set(m["titles"]))==2
        assert m["scene_key"] not in scene_ids
        scene_ids.add(m["scene_key"])
        source=base/m["source_image"]
        assert source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()==m["source_sha256"]
        assert len({x["sha256"] for x in m["images"]})==2
        for entry in m["images"]:
            img=base/entry["path"]
            assert img.is_file() and hashlib.sha256(img.read_bytes()).hexdigest()==entry["sha256"]
        if m["scene_key"] in used["used_sources"]:
            assert (base/"records"/(day+"_09_before_after.json")).exists()
print("INFINEX_THREE_DISTINCT_SIMULATED_BEFORE_AFTER_SOURCE_PAIRS_OK")

video_manifest=[]
for day,topic in (("2026-11-20","escaleras"),("2026-11-21","puertas"),
                  ("2026-11-25","cerramientos"),("2026-11-28","puertas")):
    p=base/"assets/reels"/(day+"_09_"+topic)/"sources.json"
    m=json.loads(p.read_text(encoding="utf-8"))
    assert m["date"]==day and m["slot"]=="09" and m["topic"]==topic
    f=base/m["video"]
    assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==m["video_sha256"]
    if day>="2026-11-21":
        assert m["approved_for_publish"] is True
    video_manifest.append(m)
assert len(set(m["video_sha256"] for m in video_manifest))==4
assert len(set(m["source_video_sha256"] for m in video_manifest))==4
for path in (base/"assets/reels/2026-11-23_09_puertas/sources.json",
             base/"assets/reels/2026-11-26_17_cerramientos/sources.json",
             base/"assets/reels/2026-11-25_09_puertas/sources.json",
             base/"assets/reels/2026-11-28_09_cerramientos/sources.json"):
    assert json.loads(path.read_text(encoding="utf-8"))["approved_for_publish"] is False
print("INFINEX_REELS_RESCHEDULED_25_28_NEVER_REUSED_OK")
