#!/usr/bin/env python3
"""Offline fail-closed tests: no old photo, no within-carousel duplicate and 3 different titles."""
from __future__ import annotations
import hashlib
import json
import random
import sys
import tempfile
from pathlib import Path
from PIL import Image
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base/"scripts"))
import infinex_carousel_quality as q

# Audit prior posts and deleted/rejected records, including Nov 18 manually uploaded images.
old_sources,_,old_shas,old_looks=q.used_photos(base)
assert len(old_sources)>=13,(len(old_sources),old_sources)
assert {"18379563","4671453","9163098","31302980","7540017"}<=old_sources
assert len(old_shas)>=12 and len(old_looks)>=8
print("INFINEX_HISTORICAL_IMAGE_REGISTRY_OK",len(old_sources),len(old_shas))

for theme in ("puertas","escaleras","cerramientos","soldadura"):
    all_titles=set()
    for edition in (0,4,8,12):
        titles=q.headings_for(theme,edition)
        q.validate_headings(titles)
        assert len(set(map(q.norm,titles)))==3
        assert all(q.norm(t) not in all_titles for t in titles)
        all_titles.update(map(q.norm,titles))
for invalid in (["VALLAS Y CERRAMIENTOS"]*3,["A","B","C"],
                ["Puertas metálicas","Otras puertas","Presupuesto"]):
    try:
        q.validate_headings(invalid)
        raise AssertionError("REPEATED_OR_GENERIC_HEADING_ACCEPTED")
    except RuntimeError:pass
print("INFINEX_THREE_DISTINCT_HEADLINES_TEST_OK")

with tempfile.TemporaryDirectory(prefix="infinex_originality_") as temp:
    root=Path(temp)
    assets=root/"assets"
    assets.mkdir()
    (assets/"carousel_photo_registry.json").write_text(
        json.dumps({"schema":1,"entries":[]}),encoding="utf-8")
    sub=assets/"daily"/"2026-11-25"/"09"
    sub.mkdir(parents=True)
    files=[]
    for i,seed in enumerate((11,29,53),1):
        r=random.Random(seed)
        img=Image.new("RGB",(180,210))
        img.putdata([(r.randrange(256),r.randrange(256),r.randrange(256))
                     for _ in range(180*210)])
        f=sub/f"{i:02}.jpg"
        img.save(f,"JPEG",quality=90)
        files.append({"path":str(f.relative_to(root)).replace("\\","/"),
                      "sha256":hashlib.sha256(f.read_bytes()).hexdigest()})
    manifest={"sources":[{"id":str(i)} for i in (111,222,333)],
              "images":files,
              "titles":list(q.headings_for("puertas",0))}
    assert len(q.ensure_unique(root,manifest,exclude=sub/"sources.json"))==2
    # A single photo reused as second slide fails even with another title.
    same=json.loads(json.dumps(manifest))
    same["sources"][1]["id"]="111"
    try:q.ensure_unique(root,same,exclude=sub/"sources.json");raise AssertionError("SOURCE_REPEAT_ALLOWED")
    except RuntimeError as e:assert "DUPLICATE_PHOTO_SOURCE" in str(e)
    # Same file, even under a different source id, is forbidden.
    duplicated=json.loads(json.dumps(manifest))
    duplicated["images"][1]=dict(duplicated["images"][0])
    try:q.ensure_unique(root,duplicated,exclude=sub/"sources.json");raise AssertionError("IMAGE_REPEAT_ALLOWED")
    except RuntimeError as e:assert "IMAGE_REUSED" in str(e)
    # Store historical ID, then try to reuse it in a future carousel.
    historic=assets/"daily"/"2026-11-24"/"17"
    historic.mkdir(parents=True)
    (historic/"sources.json").write_text(json.dumps({"sources":[{"id":"111"}],"images":[]}),encoding="utf-8")
    try:q.ensure_unique(root,manifest,exclude=sub/"sources.json");raise AssertionError("PAST_PHOTO_REUSED")
    except RuntimeError as e:assert "ALREADY_USED_PEXELS_ID" in str(e)
    (historic/"sources.json").unlink()
    # Old title cannot silently return in a new carousel either.
    rdata={"schema":1,"entries":[{"key":"old",
        "source_ids":[],"image_sha256":[],"hero_dhash":[],
        "titles":[manifest["titles"][0]]}]}
    (assets/"carousel_photo_registry.json").write_text(json.dumps(rdata),encoding="utf-8")
    try:q.ensure_unique(root,manifest,exclude=sub/"sources.json");raise AssertionError("PAST_TITLE_REUSED")
    except RuntimeError as e:assert "HEADLINE_ALREADY_USED" in str(e)
print("INFINEX_PREVIOUS_AND_WITHIN_CAROUSEL_NO_REUSE_TESTS_PASSED")
