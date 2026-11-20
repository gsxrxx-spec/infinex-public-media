#!/usr/bin/env python3
"""Only stage previously inspected, properly branded, unique one-topic Reels."""
import ast,hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
from infinex_editorial_policy import topic_from_caption
source=ast.parse((root/"scripts"/"infinex_reel_morning.py").read_text(encoding="utf-8"))
caption_node=next(x for x in source.body if isinstance(x,ast.Assign) and
                   any(isinstance(t,ast.Name) and t.id=="CAPTIONS" for t in x.targets))
captions=ast.literal_eval(caption_node.value)
for theme,txt in captions.items():
    assert topic_from_caption(txt)==theme,(theme,topic_from_caption(txt))
items=[("2026-11-20","escaleras"),("2026-11-21","puertas"),
       ("2026-11-22","cerramientos"),("2026-11-23","puertas")]
seen_video=set()
for day,theme in items:
    folder=root/"assets"/"reels"/(day+"_09_"+theme)
    j=json.loads((folder/"sources.json").read_text(encoding="utf-8"))
    video=root/j["video"]
    assert j["date"]==day and j["topic"]==theme
    assert j["type"]=="REELS" and j["approved_for_publish"] is True
    assert j["illustrative_ai"] is True
    assert video.is_file() and video.stat().st_size>300000
    assert hashlib.sha256(video.read_bytes()).hexdigest()==j["video_sha256"]
    assert j["video_sha256"] not in seen_video
    seen_video.add(j["video_sha256"])
print("INFINEX_MORNING_REELS_EDITORIAL_QUEUE_OK",len(items))
