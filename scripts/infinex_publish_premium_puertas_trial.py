#!/usr/bin/env python3
"""Publish one editorially approved, theme-only INFINEX metal-door carousel exactly once.

Source images are pre-rendered, licensed stock, and verified by hash.
Read back the published IG media and persist Git ledger; never blind-retry.
"""
import hashlib, json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from infinex_editorial_policy import assert_not_consecutive

BASE=Path(__file__).resolve().parents[1]
IG_ID="17841435427297631"
USER="infinex_2025"
GRAPH="https://graph.facebook.com/v27.0/"
RAW="https://raw.githubusercontent.com/gsxrxx-spec/infinex-public-media/main/"
DIR=BASE/"assets"/"campaigns"/"puertas_premium_nov2026_trial"
LEDGER=BASE/"records"/"2026-11-19_puertas_premium_trial.json"
CAPTION='¿Y si tu entrada fuera de esas que hacen que te detengas a mirar? 🟠🚪\n\nUna puerta metálica a medida no es solo un acceso: puede transformar la fachada, aportar privacidad y reflejar tu estilo.\n\nEn INFINEX trabajamos soluciones metálicas personalizadas, estudiando medidas, materiales y acabados para cada proyecto. Desde diseños minimalistas hasta accesos con carácter.\n\n📐 Adaptación a tu espacio.\n🎨 Detalles y acabados a tu gusto.\n🛠️ Una solución pensada para el uso que necesitas.\n\n¿La imaginas en tu casa o negocio? Escríbenos por mensaje privado y pide presupuesto sin compromiso.\n\n📷 Fotografías ilustrativas de archivo (Pexels). No muestran obras realizadas por INFINEX.\n\n#INFINEX #PuertasMetalicas #PuertasAMedida #Metalisteria #CarpinteriaMetalica #DisenoPersonalizado'
def log(*v):print(*v,flush=True)
def token():
    val=os.environ.get("INFINEX_IG_TOKEN","").strip()
    if len(val)<50:raise RuntimeError("IG_TOKEN_MISSING")
    return val
def api(endpoint,fields=None):
    body=urllib.parse.urlencode(fields).encode("utf-8") if fields is not None else None
    req=urllib.request.Request(GRAPH+endpoint,headers={"Authorization":"Bearer "+token(),"User-Agent":"INFINEX-Single-Topic/1.0"},
             data=body,method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=30) as res:return json.load(res)
    except urllib.error.HTTPError as err:
        raise RuntimeError("META_HTTP_"+str(err.code)) from None
    except (urllib.error.URLError,TimeoutError):
        raise RuntimeError("META_NETWORK_FAILURE") from None
def save(state):
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    temp=LEDGER.with_suffix(".tmp");temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,LEDGER)
def commit(label):
    subprocess.run(["git","config","user.name","INFINEX Scheduler"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","config","user.email","infinex-automation@users.noreply.github.com"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","add","--",str(LEDGER.relative_to(BASE))],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=BASE).returncode==0:return
    subprocess.run(["git","commit","-m","INFINEX premium puertas " + label],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","push","origin","HEAD:main"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
def verify_assets():
    manifest=json.loads((DIR/"sources.json").read_text(encoding="utf-8"))
    if (manifest.get("campaign")!="INFINEX-PUERTAS-PREMIUM-TRIAL-20261119" or
        manifest.get("theme")!="puertas_metalicas" or
        manifest.get("license")!="https://www.pexels.com/license/" or
        manifest.get("not_actual_infinex_works") is not True):
        raise RuntimeError("SOURCE_MANIFEST_INVALID")
    images=manifest.get("images",[])
    if len(images)!=3 or len(set(item["source_id"] for item in images))!=3:
        raise RuntimeError("NOT_THREE_DISTINCT_DOOR_PHOTOS")
    logo=BASE/"assets"/"branding"/"logo_infinex_original.jpg"
    if not logo.is_file() or hashlib.sha256(logo.read_bytes()).hexdigest()!=manifest["logo_sha256"]:
        raise RuntimeError("ORIGINAL_LOGO_MISMATCH")
    for item in images:
        f=BASE/item["path"]
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=item["sha256"]:
            raise RuntimeError("IMAGE_ASSET_HASH_MISMATCH")
        if not item["source_page"].startswith("https://www.pexels.com/photo/"):
            raise RuntimeError("SOURCE_PAGE_UNVERIFIED")
        req=urllib.request.Request(RAW+item["path"],headers={"User-Agent":"INFINEX-Asset-QA"})
        with urllib.request.urlopen(req,timeout=30) as res:
            contents=res.read();kind=res.headers.get("Content-Type","")
        if "image/" not in kind or hashlib.sha256(contents).hexdigest()!=item["sha256"]:
            raise RuntimeError("PUBLIC_IMAGE_HASH_MISMATCH")
    log("THEME_ONLY_CONTENT_REVIEW_OK","topic",manifest["theme"],"images",len(images))
    return images
def check_post(ident):
    post=api(str(ident)+"?fields=id,media_type,caption,permalink,children{id,media_type}")
    if (str(post.get("id"))!=str(ident) or post.get("caption")!=CAPTION or
        post.get("media_type")!="CAROUSEL_ALBUM" or
        len(post.get("children",{}).get("data",[]))!=3 or
        not post.get("permalink","").startswith("https://www.instagram.com/")):
        raise RuntimeError("READBACK_MISMATCH")
    return post
def find_existing():
    data=api(IG_ID+"/media?fields=id,caption,media_type,permalink&limit=100").get("data",[])
    for item in data:
        if item.get("caption")==CAPTION:
            return check_post(item["id"])
    return None
def enforce_distinct_from_latest():
    current=api(IG_ID+"/media?fields=id,caption,media_type,timestamp&limit=10")
    prior=assert_not_consecutive(current.get("data"),"puertas")
    log("EDITORIAL_NO_CONSECUTIVE_TOPIC_PASSED",prior or "first_post","next","puertas")

def status_ok(ident):
    for i in range(10):
        code=api(str(ident)+"?fields=status_code").get("status_code","")
        if code=="FINISHED":return
        if code in ("ERROR","EXPIRED"):raise RuntimeError("MEDIA_CONTAINER_FAILED")
        time.sleep(3)
    raise RuntimeError("MEDIA_CONTAINER_NOT_READY")
def main():
    who=api(IG_ID+"?fields=id,username")
    if str(who.get("id"))!=IG_ID or who.get("username")!=USER:
        raise RuntimeError("WRONG_INSTAGRAM_ACCOUNT")
    state=json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {}
    found=find_existing()
    if found:
        state.update({"status":"PUBLISHED_VERIFIED","account_id":IG_ID,"topic":"puertas_metalicas",
                      "media_id":str(found["id"]),"permalink":found["permalink"],
                      "caption_sha256":hashlib.sha256(CAPTION.encode()).hexdigest()})
        save(state);commit("reconciled from Meta")
        log("EDITORIAL_POST_ALREADY_EXISTS",found["permalink"]);return
    if state.get("status")=="PUBLISHED_VERIFIED":
        raise RuntimeError("PREVIOUS_VERIFIED_BUT_DELETED_NO_AUTO_REPOST")
    if state.get("publish_attempt_started"):
        raise RuntimeError("UNCONFIRMED_POST_NO_AUTOMATIC_RETRY")
    enforce_distinct_from_latest()
    images=verify_assets()
    state.update({"date":"2026-11-19","topic":"puertas_metalicas","account_id":IG_ID,
                  "caption":CAPTION,"images":images,"publish_attempt_started":False,
                  "attempt":int(state.get("attempt",0))+1,"status":"PRE_PUBLISH_PREPARED"})
    save(state);commit("prepared with licensed door images")
    try:
        children=[]
        for image in images:
            c=api(IG_ID+"/media",{"image_url":RAW+image["path"],"is_carousel_item":"true"})
            child=str(c.get("id",""))
            if not child.isdigit():raise RuntimeError("CHILD_CREATION_MISSING")
            children.append(child)
            state["children"]=children;save(state)
            status_ok(child)
        parent=api(IG_ID+"/media",{"media_type":"CAROUSEL","children":",".join(children),"caption":CAPTION})
        creation=str(parent.get("id",""))
        if not creation.isdigit():raise RuntimeError("PARENT_CREATION_MISSING")
        state["creation_id"]=creation;save(state)
        status_ok(creation)
        enforce_distinct_from_latest()
        state["status"]="PUBLISH_RESULT_UNCERTAIN_NO_RETRY"
        state["publish_attempt_started"]=True
        save(state);commit("reserved only public publish attempt")
        result=api(IG_ID+"/media_publish",{"creation_id":creation})
        post_id=str(result.get("id",""))
        if not post_id.isdigit():raise RuntimeError("PUBLISH_MEDIA_ID_MISSING")
        state["media_id"]=post_id;state["status"]="PUBLISH_SENT_READBACK_PENDING";save(state)
        for _ in range(6):
            try:
                verified=check_post(post_id)
                state.update({"status":"PUBLISHED_VERIFIED","permalink":verified["permalink"]})
                save(state);commit("published and independently verified")
                log("EDITORIAL_PUBLISHED_VERIFIED",verified["permalink"],"THEME","puertas_metalicas")
                return
            except RuntimeError:
                time.sleep(3)
        commit("readback pending do not repost")
        raise RuntimeError("PUBLISH_SENT_NOT_YET_VERIFIED")
    except Exception as exc:
        state["last_error"]=str(exc)[:75]
        if not state.get("publish_attempt_started"):
            state["status"]="PRE_PUBLISH_ERROR_SAFE_TO_RECHECK"
        save(state)
        try:commit("error-state")
        except Exception:pass
        raise
if __name__=="__main__":
    try:main()
    except Exception as e:
        log("EDITORIAL_ERROR",str(e)[:110])
        sys.exit(1)
