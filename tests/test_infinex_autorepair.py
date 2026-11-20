#!/usr/bin/env python3
"""No Instagram traffic: prove editorial auto-repair changes material, not the rules."""
from __future__ import annotations
import random
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
import infinex_daily as daily
from infinex_autorepair import alternate_topics,unique_headlines
from infinex_carousel_quality import norm,headings_for,validate_headings

assert alternate_topics("puertas","escaleras")==["puertas","cerramientos","soldadura"]
used=[]
for e in range(4):
    used.extend(headings_for("cerramientos",e*4))
replacement=unique_headlines("cerramientos",64,used)
validate_headings(replacement)
assert len(set(map(norm,replacement)))==3
assert not(set(map(norm,replacement)) & set(map(norm,used)))
print("AUTOREPAIR_NEW_DISTINCT_COPY_OK")

orig=(daily.prepare_editorial_plan,daily.build,daily.caption_for,
      daily.review_before_publish,daily.EDITORIAL_THEME)
attempts=[]
try:
    def prepare(previous,failed):
        theme="puertas" if "puertas" not in failed else "cerramientos"
        daily.EDITORIAL_THEME=theme
        attempts.append(("prepare",theme))
    def build():
        theme=daily.topic_for_slot()
        attempts.append(("build",theme))
        if theme=="puertas":raise RuntimeError("EDITORIAL_SOURCE_PHOTO_REJECTED")
        return [("gates",{"id":"demo_1"})],{"titles":["ABC","XYZ","CTA"]}
    daily.prepare_editorial_plan=prepare
    daily.build=build
    daily.caption_for=lambda selected:"UNIQUE_PROMOTIONAL_TEXT"
    daily.review_before_publish=lambda *args: None
    selected,manifest,copy=daily.regenerate_until_approved("escaleras")
    assert attempts==[("prepare","puertas"),("build","puertas"),
                      ("prepare","cerramientos"),("build","cerramientos")]
    assert copy=="UNIQUE_PROMOTIONAL_TEXT"
    print("AUTOREPAIR_REJECTED_TOPIC_REPLACED_BEFORE_PUBLISH_OK")
finally:
    (daily.prepare_editorial_plan,daily.build,daily.caption_for,
     daily.review_before_publish,daily.EDITORIAL_THEME)=orig

# A broken original photograph must be replaceable with a different licensed
# source without changing the carousel's required three different headlines.
with TemporaryDirectory(prefix="infinex_repair_") as d:
    folder=Path(d)
    original=(daily.BASE,daily.MEDIA_DIR,daily.photo_candidates,
              daily.download_photo,daily.render_slide,daily.used_photos,
              daily.EDITORIAL_THEME,daily.EDITORIAL_TITLES)
    try:
        daily.BASE=folder
        daily.MEDIA_DIR=folder/"assets/daily/2026-11-21/17"
        daily.EDITORIAL_THEME="cerramientos"
        daily.EDITORIAL_TITLES=("UN JARDÍN DIFERENTE","MÁS PRIVACIDAD","CUÉNTANOS TU IDEA")
        daily.photo_candidates=lambda theme:[("gates",{"id":str(n),"page":"https://www.pexels.com/photo/photo-"+str(n),"author":"Illustrative"}) for n in range(1,5)]
        def download(photo):
            if photo["id"]=="1":raise RuntimeError("EDITORIAL_LOW_QUALITY_REPLACE")
            return int(photo["id"])
        daily.download_photo=download
        def render(number,category,idx,out):
            rng=random.Random(number*101)
            pixels=[(rng.randrange(256),rng.randrange(256),rng.randrange(256))
                    for _ in range(200*250)]
            image=Image.new("RGB",(200,250))
            image.putdata(pixels)
            image.save(out,quality=92)
        daily.render_slide=render
        daily.used_photos=lambda *args,**kwargs:(set(),set(),set(),set())
        folder.joinpath("assets/branding").mkdir(parents=True)
        # Dummy original logo (only existence checked by build in this test).
        (folder/"assets/branding/logo_infinex_original.jpg").write_bytes(b"demo")
        chosen,manifest=daily.build()
        assert [p["id"] for _,p in chosen]==["2","3","4"]
        assert len(manifest["images"])==3
        assert manifest["titles"]==list(daily.EDITORIAL_TITLES)
        print("AUTOREPAIR_BAD_IMAGE_REPLACED_WITH_UNIQUE_NEW_SOURCE_OK")
    finally:
        (daily.BASE,daily.MEDIA_DIR,daily.photo_candidates,
         daily.download_photo,daily.render_slide,daily.used_photos,
         daily.EDITORIAL_THEME,daily.EDITORIAL_TITLES)=original
print("AUTOREPAIR_OFFLINE_TESTS_PASSED")
