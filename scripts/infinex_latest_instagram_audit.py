#!/usr/bin/env python3
"""Read-only audit of the latest INFINEX Instagram media (no publishing)."""
import os, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageStat
ID="17841435427297631"
ROOT="https://graph.facebook.com/v27.0/"
token=os.getenv("INFINEX_IG_TOKEN","").strip()
if len(token)<50: raise RuntimeError("MISSING_IG_SECRET")
def fetch(path):
    req=urllib.request.Request(ROOT+path,headers={"Authorization":"Bearer "+token,"User-Agent":"INFINEX-Audit/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        try: err=json.loads(e.read(1500)).get("error",{})
        except Exception: err={}
        raise RuntimeError("META_HTTP_"+str(e.code)+"_CODE_"+str(err.get("code","UNKNOWN"))) from None
identity=fetch(ID+"?fields=id,username")
if str(identity.get("id"))!=ID or identity.get("username")!="infinex_2025":raise RuntimeError("IG_IDENTITY_BAD")
posts=fetch(ID+"/media?fields=id,media_type,timestamp,permalink,caption,children{id,media_type,media_url}&limit=12").get("data",[])
print("IG_ACCOUNT_VERIFIED", identity["username"])
for i,post in enumerate(posts):
    child=post.get("children",{}).get("data",[])
    caption=post.get("caption","")
    print("IG_POST",i,"ID",post.get("id"),"TYPE",post.get("media_type"),"TIME",post.get("timestamp"),"CHILD_COUNT",len(child),"CAPTION_SHA",__import__("hashlib").sha256(caption.encode()).hexdigest(),"CAPTION_SIZE",len(caption),"URL",post.get("permalink",""))
    print("CAPTION_TEXT_START",i,repr(caption[:350]))
    for j,item in enumerate(child):
        print("IG_CHILD",i,j,item.get("id"),item.get("media_type"),"HAS_MEDIA_URL",bool(item.get("media_url")))
latest=posts[0] if posts else None
if latest and latest.get("media_type")=="CAROUSEL_ALBUM":
    candidates=sorted((Path(__file__).resolve().parents[1]/"assets"/"2026-11-18"/"visual-b").glob("*.jpg"))
    print("LOCAL_2026_11_18_IMAGE_COUNT",len(candidates))
    for j,item in enumerate(latest.get("children",{}).get("data",[])):
        url=item.get("media_url","")
        try:
            if not url.startswith("https://"):
                raise ValueError("MISSING_HTTPS_MEDIA_URL")
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=25) as r:
                remote=Image.open(BytesIO(r.read())).convert("RGB").resize((100,120))
            scored=[]
            for file in candidates:
                sample=Image.open(file).convert("RGB").resize((100,120))
                diffs=ImageStat.Stat(__import__("PIL.ImageChops",fromlist=["difference"]).difference(remote,sample)).mean
                score=round(1-sum(diffs)/(3*255),4)
                scored.append((file.name,score))
            print("IG_IMAGE_MATCH",j,sorted(scored,key=lambda x:-x[1]))
        except Exception as e:
            print("IG_IMAGE_MATCH_UNAVAILABLE",j,type(e).__name__)
print("IG_AUDIT_READ_ONLY_FINISHED")
