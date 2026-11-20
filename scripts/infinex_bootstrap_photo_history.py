#!/usr/bin/env python3
"""One-time historical snapshot; conservative even for posts user removed."""
from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
from infinex_carousel_quality import manifest_paths, file_image_signature,REGISTRY
destination=root/REGISTRY
if destination.exists():raise SystemExit("HISTORICAL_REGISTRY_ALREADY_EXISTS")
entries=[]
for path in sorted(manifest_paths(root)):
    m=json.loads(path.read_text(encoding="utf-8-sig"))
    ids=[str(s["id"]) for s in m.get("sources",[]) if s.get("id")]
    ids += [str(s["source_id"]) for s in m.get("images",[]) if s.get("source_id")]
    ids=list(dict.fromkeys(ids))
    filepaths=[]
    for photo in m.get("images",[]):
        f=root/photo.get("path","")
        if f.is_file():filepaths.append(f)
    files_sha=[hashlib.sha256(x.read_bytes()).hexdigest() for x in filepaths]
    dhash=[file_image_signature(x) for x in filepaths]
    entries.append({"key":"historical:"+str(path.relative_to(root)).replace("\\","/"),
                    "source_ids":ids,"image_sha256":files_sha,"hero_dhash":dhash,
                    "titles":m.get("titles",[]),"status":"HISTORICAL_LOCKED"})
# First two November 18 carousels predate Pexels manifest tracking.
for folder in (root/"assets/2026-11-18",root/"assets/2026-11-18/visual-b"):
    photos=sorted(folder.glob("*.jpg"))
    if not photos:continue
    entries.append({"key":"historical:"+str(folder.relative_to(root)).replace("\\","/"),
                    "source_ids":[],"image_sha256":[hashlib.sha256(f.read_bytes()).hexdigest() for f in photos],
                    "hero_dhash":[file_image_signature(f) for f in photos],
                    "titles":[],"status":"HISTORICAL_LOCKED_UNKNOWN_ORIGINAL_SOURCE_ID"})
data={"schema":1,"policy":"Every source photo is one-time only; all historical reservations survive deletions.", "entries":entries}
destination.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("HISTORICAL_PHOTOS_LOCKED",len(entries),"SOURCE_IDS",
      len(set(y for x in entries for y in x["source_ids"])),"ASSET_HASHES",
      sum(len(x["image_sha256"]) for x in entries))
