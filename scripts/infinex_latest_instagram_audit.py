#!/usr/bin/env python3
"""Read-only audit of the latest INFINEX Instagram media (no publishing)."""
import os, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime
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
print("IG_AUDIT_READ_ONLY_FINISHED")
