#!/usr/bin/env python3
"""Fail-closed protection against replaying any known INFINEX Instagram Reel.

Checks both the rendered video SHA256 and its *source* video SHA256, so a
re-edited/re-captioned version of the same footage cannot be scheduled.
Published/uncertain records are read from live GitHub origin/main and local
ledger; old/deleted publications retain their historic fingerprint.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

BLOCKED_STATUSES = {
    "PUBLISHED_VERIFIED", "PUBLISH_SENT_VERIFY_PENDING",
    "PUBLISHING_UNCERTAIN_DO_NOT_RETRY", "DO_NOT_REPOST",
    "REJECTED_BY_USER", "PUBLISH_SENT_READBACK_PENDING",
}

def command(args,base:Path) -> str:
    p=subprocess.run(["git",*args],cwd=base,stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL,text=True,timeout=35)
    if p.returncode!=0:
        raise RuntimeError("INFINEX_REEL_GIT_LEDGER_UNAVAILABLE")
    return p.stdout

def latest_ledger(base:Path) -> list[dict]:
    # Read live origin; do not trust an outdated workflow checkout.
    command(["fetch","--quiet","origin","main"],base)
    remote=command(["ls-tree","-r","--name-only","origin/main","records"],base)
    histories={}
    for name in remote.splitlines():
        if not name.endswith("_reel.json"):
            continue
        try:
            obj=json.loads(command(["show","origin/main:"+name],base))
        except (ValueError,RuntimeError) as e:
            raise RuntimeError("INFINEX_REEL_INVALID_HISTORICAL_LEDGER") from e
        histories[name]=obj
    for entry in (base/"records").glob("*_reel.json"):
        try: local=json.loads(entry.read_text(encoding="utf-8"))
        except ValueError as e:raise RuntimeError("INFINEX_REEL_INVALID_LOCAL_LEDGER") from e
        prior=histories.get("records/"+entry.name)
        if prior is None:
            histories["records/"+entry.name]=local
        elif local!=prior:
            # Conservatively retain both snapshots (e.g. workflow reserved
            # publish locally but push failed due to a concurrent update).
            histories["local:"+entry.name]=local
    return list(histories.values())

def get_published_source(base:Path, rec:dict) -> str|None:
    v=rec.get("source_video_sha256")
    if v: return v
    date,slot,topic=rec.get("date"),rec.get("slot"),rec.get("topic")
    if not (date and slot and topic):return None
    path=base/"assets"/"reels"/(str(date)+"_"+str(slot)+"_"+str(topic))/"sources.json"
    if not path.exists():return None
    try: return json.loads(path.read_text(encoding="utf-8")).get("source_video_sha256")
    except ValueError:raise RuntimeError("INFINEX_REEL_PUBLISHED_SOURCE_INVALID")

def validate_unique(base:Path,asset:dict,day:str,slot:str)->None:
    video=asset.get("video_sha256","")
    source=asset.get("source_video_sha256","")
    if (not isinstance(video,str) or len(video)!=64 or
        not isinstance(source,str) or len(source)!=64):
        raise RuntimeError("INFINEX_REEL_SOURCE_HASH_REQUIRED")

    # Permanently blocked historical fingerprints survive deletes.
    historic=base/"assets"/"reels"/"NEVER_REUSE.json"
    if not historic.exists():raise RuntimeError("INFINEX_REEL_BLOCKLIST_MISSING")
    obj=json.loads(historic.read_text(encoding="utf-8"))
    for used in obj.get("used",[]):
        if video==used.get("video_sha256") or source==used.get("source_video_sha256"):
            raise RuntimeError("INFINEX_REEL_ALREADY_USED_SOURCE_BLOCKED")

    # Fail if another preapproved future Reel contains the same original clip.
    for f in (base/"assets"/"reels").glob("*/sources.json"):
        candidate=json.loads(f.read_text(encoding="utf-8"))
        if not candidate.get("approved_for_publish"):continue
        if (candidate.get("date"),candidate.get("slot"))==(day,slot):continue
        if (candidate.get("video_sha256")==video or
            candidate.get("source_video_sha256")==source):
            raise RuntimeError("INFINEX_REEL_DUPLICATE_APPROVED_FOOTAGE")

    for record in latest_ledger(base):
        same_slot=(record.get("date"),record.get("slot"))==(day,slot)
        used=(record.get("publish_attempt_started") or
              record.get("status") in BLOCKED_STATUSES)
        if same_slot and used:
            # Another job may have committed an irreversible attempt after
            # this run checked out an older SHA. Fail instead of re-posting.
            raise RuntimeError("INFINEX_REEL_SLOT_ALREADY_PUBLISHED_OR_RESERVED")
        if not used:
            continue
        known_video=record.get("video_sha256")
        known_source=get_published_source(base,record)
        if known_video and video==known_video:
            raise RuntimeError("INFINEX_REEL_PREVIOUSLY_PUBLISHED_HASH")
        if known_source and source==known_source:
            raise RuntimeError("INFINEX_REEL_PREVIOUSLY_PUBLISHED_SOURCE")

def caption_reusable_media_item(item:dict,caption:str,day:str)->bool:
    """Only reconcile a caption-matching post from the same Madrid calendar day.

    Older posts with the same caption cannot count as today's successful Reel.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if item.get("caption")!=caption:return False
    ts=item.get("timestamp")
    if not ts:raise RuntimeError("INFINEX_REEL_EXISTING_POST_DATE_UNKNOWN")
    try:
        posted=datetime.strptime(ts,"%Y-%m-%dT%H:%M:%S%z")
        local_day=posted.astimezone(ZoneInfo("Europe/Madrid")).date().isoformat()
    except ValueError as e:
        raise RuntimeError("INFINEX_REEL_EXISTING_POST_TIMESTAMP_INVALID") from e
    if local_day!=day:
        raise RuntimeError("INFINEX_REEL_CAPTION_REUSED_ANOTHER_DAY")
    return True
