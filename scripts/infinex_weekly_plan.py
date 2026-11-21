#!/usr/bin/env python3
"""INFINEX calendario: UNA publicacion diaria a las 09:30 Europe/Madrid.

Vigente desde el domingo 22/11/2026: 2 Reels, 3 antes/despues,
2 carruseles informativos por semana. No alterar el sábado 21 ya programado.
"""
from __future__ import annotations
from datetime import date,datetime,time as dtime
from zoneinfo import ZoneInfo
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
def scheduled_posts(day:date)->tuple[tuple[str,str],...]:
    if day>=CHANGE_DATE:return WEEKLY_PLAN[day.weekday()]
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
