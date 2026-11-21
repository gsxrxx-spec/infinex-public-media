#!/usr/bin/env python3
"""Compatibility QA: 7/day plan, 2 unique weekly Reels, zero replay of footage."""
import ast,hashlib,json,sys
from pathlib import Path
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base/"scripts"))
from infinex_editorial_policy import topic_from_caption
import test_infinex_weekly_seven  # validates calendar and manifests
from infinex_reel_uniqueness import validate_unique, caption_reusable_media_item

tree=ast.parse((base/"scripts/infinex_reel_morning.py").read_text(encoding="utf-8"))
node=next(x for x in tree.body if isinstance(x,ast.Assign)
          and any(isinstance(v,ast.Name) and v.id=="CAPTIONS" for v in x.targets))
captions=ast.literal_eval(node.value)
for topic,txt in captions.items():
    assert topic_from_caption(txt)==topic

history=json.loads((base/"assets/reels/NEVER_REUSE.json").read_text(encoding="utf-8"))
previous=next(x for x in history["used"] if x["date"]=="2026-11-20")
test={"video_sha256":"a"*64,"source_video_sha256":previous["source_video_sha256"]}
try:
    validate_unique(base,test,"2026-12-03","09")
    raise AssertionError("REEL_SOURCE_REPLAY_NOT_BLOCKED")
except RuntimeError as e:
    assert "ALREADY_USED" in str(e)
cap="Puertas metálicas con estilo #PuertasMetalicas"
try:
    caption_reusable_media_item({"caption":cap,"timestamp":"2026-11-20T09:17:43+0000"},cap,"2026-11-25")
    raise AssertionError("OLD_REEL_RECONCILED_WRONG_DAY")
except RuntimeError as e:
    assert "CAPTION_REUSED_ANOTHER_DAY" in str(e)
print("INFINEX_2026_NEW_SEVEN_PLAN_REEL_UNIQUENESS_TEST_OK")
