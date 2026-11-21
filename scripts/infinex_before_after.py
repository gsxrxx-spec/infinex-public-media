#!/usr/bin/env python3
"""INFINEX before/after publisher, one correct simulated transformation per slot.

Never identify an AI/retouched concept as a real customer installation.
Meta single-publish guarded by a durable ledger and permanent source registry.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image
from infinex_weekly_plan import TZ,is_scheduled,due,review_due
from infinex_editorial_policy import assert_not_consecutive,topic_from_caption
from infinex_carousel_quality import used_photos

BASE=Path(__file__).resolve().parents[1]
NOW=datetime.now(TZ);DAY=NOW.date();DATE=DAY.isoformat()
SLOT="09"
IG_ID="17841435427297631";IG_USERNAME="infinex_2025"
GRAPH="https://graph.facebook.com/v27.0/"
RAW="https://raw.githubusercontent.com/gsxrxx-spec/infinex-public-media/main/"
REGISTRY="assets/before_after/USED_SCENES.json"
LEDGER=BASE/"records"/(DATE+"_09_before_after.json")
MODE=sys.argv[1] if len(sys.argv)>1 else "recover"
if MODE not in ("recover","publish","dry_run","verify"):raise SystemExit(2)

def log(*a):print(*a,flush=True)
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,path)
def read_json(p):return json.loads(p.read_text(encoding="utf-8"))
def media_paths():
    return list((BASE/"assets"/"before_after").glob(DATE+"_09_*/sources.json"))
def manifest():
    candidates=media_paths()
    if len(candidates)!=1:raise RuntimeError("INFINEX_BEFORE_AFTER_APPROVED_ASSET_COUNT_NOT_ONE")
    m=read_json(candidates[0])
    if (m.get("approved_for_publish") is not True or
        m.get("illustrative_simulation") is not True or
        m.get("not_actual_infinex_works") is not True or
        m.get("source_license")!="https://www.pexels.com/license/" or
        m.get("date")!=DATE or m.get("slot")!="09" or
        m.get("type")!="BEFORE_AFTER"):
        raise RuntimeError("INFINEX_BEFORE_AFTER_NOT_APPROVED_OR_INCONSISTENT")
    if len(m.get("images",[]))!=2 or len(set(m.get("titles",[])))!=2:
        raise RuntimeError("INFINEX_BEFORE_AFTER_REQUIRES_TWO_DISTINCT_SLIDES")
    if m.get("scene_key") is None or not m["scene_key"].startswith("pexels:"):
        raise RuntimeError("INFINEX_BEFORE_AFTER_SOURCE_UNKNOWN")
    if len(m.get("source_sha256",""))!=64:
        raise RuntimeError("INFINEX_BEFORE_AFTER_SOURCE_HASH_MISSING")
    f=BASE/m["source_image"]
    if not f.exists() or sha(f)!=m["source_sha256"]:
        raise RuntimeError("INFINEX_BEFORE_AFTER_SOURCE_CHANGED")
    if sha(BASE/"assets/branding/logo_infinex_original.jpg")!=m.get("logo_sha256"):
        raise RuntimeError("INFINEX_BEFORE_AFTER_LOGO_INVALID")
    for entry in m["images"]:
        f=BASE/entry["path"]
        if not f.is_file() or sha(f)!=entry["sha256"]:
            raise RuntimeError("INFINEX_BEFORE_AFTER_OUTPUT_HASH_INVALID")
        with Image.open(f) as picture:
            if picture.size!=(1080,1350) or picture.format!="JPEG":
                raise RuntimeError("INFINEX_BEFORE_AFTER_IMAGE_NOT_1080x1350")
    if m["images"][0]["sha256"]==m["images"][1]["sha256"]:
        raise RuntimeError("INFINEX_BEFORE_AFTER_NO_VISIBLE_CHANGE")
    return m
def caption(m):
    subject={
        "puertas":"puerta metálica de acceso",
        "cerramientos":"cerramiento metálico",
        "escaleras":"escalera metálica"
    }.get(m["topic"])
    if not subject:raise RuntimeError("INFINEX_BEFORE_AFTER_UNKNOWN_SERVICE")
    # Disclaimer must be visible inside both images AND the caption.
    text=(
        "INFINEX | ANTES Y DESPUÉS · "+DATE+"\n\n"
        "¿Y si este espacio cambiara por completo con un "+subject+"? 🟠\n\n"
        "1️⃣ ANTES: el acceso sin el elemento metálico.\n"
        "2️⃣ DESPUÉS: cómo podría quedar con una solución diseñada a medida.\n\n"
        "Cada proyecto exige estudiar medidas, materiales, anclajes y acabados. "
        "Si tienes una entrada o una zona por transformar, escríbenos y "
        "pide presupuesto sin compromiso.\n\n"
        "⚠️ Simulación digital ilustrativa sobre una fotografía de archivo de Pexels. "
        "No corresponde a una instalación real realizada por INFINEX.\n"
        "Foto de "+m["source_author"]+" (Pexels).\n\n"
        "#INFINEX #AntesYDespues #Metalisteria"
    )
    # Explicit topic identifier for fail-closed consecutive-theme reader.
    return text+" #"+{"puertas":"PuertasMetalicas",
                     "cerramientos":"CerramientosMetalicos",
                     "escaleras":"EscalerasMetalicas"}[m["topic"]]
def token():
    s=os.getenv("INFINEX_IG_TOKEN","").strip()
    if len(s)<50:raise RuntimeError("INFINEX_IG_TOKEN_NOT_CONFIGURED")
    return s
def api(endpoint,form=None):
    req=urllib.request.Request(GRAPH+endpoint,
        data=urllib.parse.urlencode(form).encode("utf-8") if form is not None else None,
        headers={"Authorization":"Bearer "+token(),"User-Agent":"INFINEX-BeforeAfter/1.0"},
        method="POST" if form is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=32) as resp:return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("INFINEX_META_HTTP_"+str(exc.code)) from None
    except (urllib.error.URLError,TimeoutError):
        raise RuntimeError("INFINEX_META_NETWORK_FAILED") from None
def commit(message):
    subprocess.run(["git","config","user.name","INFINEX Scheduler"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","config","user.email","infinex-automation@users.noreply.github.com"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    paths=[str(LEDGER.relative_to(BASE)),REGISTRY]
    subprocess.run(["git","add","--",*paths],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=BASE).returncode==0:return
    subprocess.run(["git","commit","-m",message],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","push","origin","HEAD:main"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)

def verify_existing(mid,cap):
    p=api(str(mid)+"?fields=id,caption,media_type,permalink,timestamp,children{id}")
    if (str(p.get("id"))!=str(mid) or p.get("caption")!=cap or
        p.get("media_type")!="CAROUSEL_ALBUM" or
        len(p.get("children",{}).get("data",[]))!=2 or
        not p.get("permalink","").startswith("https://www.instagram.com/")):
        raise RuntimeError("INFINEX_BEFORE_AFTER_META_READBACK_FAILED")
    return p

def current_media():
    return api(IG_ID+"/media?fields=id,caption,media_type,permalink,timestamp&limit=100").get("data",[])

def sources_available(m):
    registry=read_json(BASE/REGISTRY)
    # Reserve source even if another scheduled slot is interrupted.
    blocked_ids=set(registry.get("used_sources",[]))
    if m["scene_key"] in blocked_ids:
        raise RuntimeError("INFINEX_BEFORE_AFTER_SCENE_USED_OR_RESERVED")
    # Cross-check the historical carousel photo bank too.
    used,_,_,_=used_photos(BASE)
    if m["scene_key"].split(":")[1] in used:
        raise RuntimeError("INFINEX_BEFORE_AFTER_SOURCE_USED_IN_OTHER_CAROUSEL")
    for folder in (BASE/"assets/before_after").glob("*/sources.json"):
        if folder.parent.name.startswith(DATE+"_"):continue
        other=read_json(folder)
        if other.get("scene_key")==m["scene_key"]:
            raise RuntimeError("INFINEX_BEFORE_AFTER_SCENE_REPEATED_IN_ANOTHER_POST")
    return registry

def public_images(m):
    for img in m["images"]:
        url=RAW+img["path"]
        req=urllib.request.Request(url,headers={"User-Agent":"INFINEX-Public-Readiness"})
        with urllib.request.urlopen(req,timeout=32) as resp:
            if not resp.headers.get("Content-Type","").startswith("image/"):
                raise RuntimeError("INFINEX_BEFORE_AFTER_PUBLIC_SOURCE_NOT_IMAGE")
            content=resp.read()
        if hashlib.sha256(content).hexdigest()!=img["sha256"]:
            raise RuntimeError("INFINEX_BEFORE_AFTER_PUBLIC_IMAGE_HASH_MISMATCH")

def status(cid):
    for _ in range(20):
        s=api(str(cid)+"?fields=status_code").get("status_code")
        if s=="FINISHED":return
        if s in ("ERROR","EXPIRED"):raise RuntimeError("INFINEX_BEFORE_AFTER_MEDIA_CONTAINER_ERROR")
        time.sleep(3)
    raise RuntimeError("INFINEX_BEFORE_AFTER_CONTAINER_NOT_READY")

def publish():
    if not due(DAY,SLOT,"before_after",NOW):
        log("BEFORE_AFTER_NOT_DUE",DATE);return
    m=manifest()
    cap=caption(m)
    state=read_json(LEDGER) if LEDGER.exists() else {}
    if state.get("status")=="PUBLISHED_VERIFIED" or state.get("do_not_republish"):
        log("BEFORE_AFTER_ALREADY_DONE_OR_REJECTED",DATE);return
    for old in current_media():
        if old.get("caption")==cap:
            p=verify_existing(old["id"],cap)
            state.update({"status":"PUBLISHED_VERIFIED","media_id":p["id"],
                          "permalink":p["permalink"],"caption":cap,
                          "date":DATE,"slot":SLOT})
            write_json(LEDGER,state);commit("INFINEX reconcile before-after "+DATE)
            log("BEFORE_AFTER_ALREADY_PUBLISHED",p["permalink"]);return
    if state.get("publish_attempt_started") or state.get("creation_id"):
        raise RuntimeError("INFINEX_BEFORE_AFTER_UNCERTAIN_NO_DUPLICATE_RETRY")
    account=api(IG_ID+"?fields=id,username")
    if str(account.get("id"))!=IG_ID or account.get("username")!=IG_USERNAME:
        raise RuntimeError("INFINEX_BEFORE_AFTER_WRONG_ACCOUNT")
    current=current_media()
    assert_not_consecutive(current,m["topic"])
    registry=sources_available(m)
    public_images(m)
    state={"date":DATE,"slot":SLOT,"status":"PREPARED",
           "topic":m["topic"],"caption":cap,"scene_key":m["scene_key"],
           "source_sha256":m["source_sha256"],"images":m["images"],
           "children":[],"publish_attempt_started":False}
    # Permanently reserve the photo source and media content before first Meta POST.
    registry["used_sources"].append(m["scene_key"])
    registry.setdefault("used_days",[]).append(DATE)
    write_json(BASE/REGISTRY,registry)
    write_json(LEDGER,state);commit("INFINEX reserve before-after original scene "+DATE)
    try:
        for img in m["images"]:
            c=api(IG_ID+"/media",{"image_url":RAW+img["path"],"is_carousel_item":"true"})
            cid=str(c.get("id",""))
            if not cid.isdigit():raise RuntimeError("INFINEX_BEFORE_AFTER_CHILD_ID_INVALID")
            state["children"].append(cid)
            write_json(LEDGER,state)
            status(cid)
        c=api(IG_ID+"/media",{"media_type":"CAROUSEL",
            "children":",".join(state["children"]),"caption":cap})
        cid=str(c.get("id",""))
        if not cid.isdigit():raise RuntimeError("INFINEX_BEFORE_AFTER_PARENT_ID_INVALID")
        state["creation_id"]=cid;state["status"]="CONTAINER_CREATED"
        write_json(LEDGER,state);commit("INFINEX record before-after container "+DATE)
        status(cid)
        assert_not_consecutive(current_media(),m["topic"])
        state["publish_attempt_started"]=True
        state["status"]="PUBLISHING_UNCERTAIN_NO_RETRY"
        write_json(LEDGER,state);commit("INFINEX irreversible before-after reservation "+DATE)
        result=api(IG_ID+"/media_publish",{"creation_id":cid})
        mid=str(result.get("id",""))
        if not mid.isdigit():raise RuntimeError("INFINEX_BEFORE_AFTER_MEDIA_ID_MISSING")
        state["media_id"]=mid;state["status"]="SENT_VERIFY_PENDING";write_json(LEDGER,state)
        for _ in range(8):
            try:
                p=verify_existing(mid,cap)
                state.update({"status":"PUBLISHED_VERIFIED","permalink":p["permalink"],
                              "timestamp":p.get("timestamp")})
                write_json(LEDGER,state);commit("INFINEX before-after published verified "+DATE)
                log("INFINEX_BEFORE_AFTER_PUBLISHED_VERIFIED",p["permalink"]);return
            except RuntimeError:time.sleep(4)
        raise RuntimeError("INFINEX_BEFORE_AFTER_SENT_READBACK_PENDING")
    except Exception as exc:
        state["error_code"]=str(exc)[:100]
        if not state.get("publish_attempt_started"):state["status"]="PRE_PUBLISH_FAILED_REVIEW_REQUIRED"
        write_json(LEDGER,state)
        try:commit("INFINEX before-after failure record "+DATE)
        except Exception:pass
        raise

def verify():
    if not review_due(DAY,SLOT,"before_after",NOW):
        log("BEFORE_AFTER_REVIEW_NOT_DUE",DATE);return
    if not LEDGER.exists():raise RuntimeError("INFINEX_BEFORE_AFTER_REVIEW_LEDGER_NOT_FOUND")
    state=read_json(LEDGER)
    if not state.get("media_id"):raise RuntimeError("INFINEX_BEFORE_AFTER_REVIEW_NO_MEDIA_ID")
    post=verify_existing(state["media_id"],state["caption"])
    state.update({"status":"PUBLISHED_VERIFIED","permalink":post["permalink"],
                  "reviewed_at":datetime.now(TZ).isoformat()})
    write_json(LEDGER,state);commit("INFINEX before-after independent review "+DATE)
    log("INFINEX_BEFORE_AFTER_INDEPENDENTLY_VERIFIED",post["permalink"])

def main():
    if not is_scheduled(DAY,SLOT,"before_after"):
        log("INFINEX_BEFORE_AFTER_NOT_SCHEDULED",DATE);return
    if MODE=="dry_run":
        m=manifest()
        log("INFINEX_BEFORE_AFTER_APPROVED_DRYRUN",DATE,m["scene_key"],len(m["images"]))
    elif MODE=="publish":publish()
    elif MODE=="verify":verify()
    else:
        # Late-safe main and post-publication review; failed auth/unknown result
        # remain a genuine incident, never blindly reposted.
        if due(DAY,SLOT,"before_after",NOW):publish()
        if review_due(DAY,SLOT,"before_after",NOW):verify()

if __name__=="__main__":
    try:main()
    except Exception as exc:
        log("INFINEX_BEFORE_AFTER_ERROR",str(exc)[:120])
        raise SystemExit(1)
