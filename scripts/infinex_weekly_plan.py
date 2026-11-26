#!/usr/bin/env python3
"""INFINEX calendario: UNA publicacion diaria a las 09:30 Europe/Madrid.

Vigente desde el domingo 22/11/2026: 2 Reels, 3 antes/despues,
2 carruseles informativos por semana. No alterar el sábado 21 ya programado.
"""
from __future__ import annotations
from datetime import date,datetime,time as dtime
from zoneinfo import ZoneInfo
from pathlib import Path
import json
TZ=ZoneInfo("Europe/Madrid")
START_DATE=date(2026,11,21)
CHANGE_DATE=date(2026,11,22)
# 0 lunes ... 6 domingo
WEEKLY_PLAN={
  0:(("09","informative"),),
  1:(("09","before_after"),),
  2:(("09","reel"),),
  3:(("09","before_after"),),
  4:(("09","informative"),),
  5:(("09","reel"),),
  6:(("09","before_after"),),
}
# Preserve the current Saturday's previously authorized two slots.
TRANSITION={date(2026,11,21):(("09","reel"),("17","carousel"))}
BASE=Path(__file__).resolve().parents[1]
def approved_fallback(day:date):
    if day<CHANGE_DATE:return None
    original=WEEKLY_PLAN[day.weekday()][0][1]
    if original=="informative":return None
    p=BASE/"assets"/"daily"/day.isoformat()/"09"/"sources.json"
    if not p.is_file():return None
    m=json.loads(p.read_text(encoding="utf-8"))
    if m.get("fallback_approved") is not True:return None
    if (m.get("date")!=day.isoformat() or m.get("slot")!="09" or
        m.get("fallback_from")!=original or
        m.get("visual_review",{}).get("status")!="APPROVED_BY_SYSTEM_VISUAL_REVIEW"):
        raise RuntimeError("INFINEX_FALLBACK_MANIFEST_INVALID")
    # Never replace a slot which already has another format's public attempt.
    for suffix in ("_09_before_after.json","_09_reel.json"):
        if (BASE/"records"/(day.isoformat()+suffix)).is_file():
            raise RuntimeError("INFINEX_FALLBACK_OTHER_FORMAT_RECORD_REQUIRES_RECONCILIATION")
    return m
def scheduled_posts(day:date)->tuple[tuple[str,str],...]:
    if day>=CHANGE_DATE:
        if approved_fallback(day):return (("09","informative"),)
        return WEEKLY_PLAN[day.weekday()]
    return TRANSITION.get(day,())
def scheduled_post(day:date):
    items=scheduled_posts(day)
    return items[0] if items else None
def is_scheduled(day:date,slot:str,kind:str)->bool:
    # "carousel" on the new calendar means only the informative format.
    if day>=CHANGE_DATE and kind=="carousel":kind="informative"
    return (slot,kind) in scheduled_posts(day)
def publish_hour_minute(day:date,slot:str)->tuple[int,int]:
    if day>=CHANGE_DATE:return (9,30)
    return int(slot),0
def due(day:date,slot:str,kind:str,now:datetime|None=None)->bool:
    if not is_scheduled(day,slot,kind):return False
    now=(now or datetime.now(TZ)).astimezone(TZ)
    hour,minute=publish_hour_minute(day,slot)
    return now.date()>day or (now.date()==day and now.time()>=dtime(hour,minute))
def review_due(day:date,slot:str,kind:str,now:datetime|None=None)->bool:
    if not is_scheduled(day,slot,kind):return False
    now=(now or datetime.now(TZ)).astimezone(TZ)
    hh,mm=publish_hour_minute(day,slot)
    mm+=15
    return now.date()>day or (now.date()==day and now.time()>=dtime(hh,mm))
