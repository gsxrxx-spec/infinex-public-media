#!/usr/bin/env python3
"""INFINEX 09:00 Europe/Madrid Reel publisher. Meta API; only pre-approved video.
Safe retries after downtime, no duplicate/uncertain media_publish retries.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,date,time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo
from infinex_editorial_policy import assert_not_consecutive,TOPICS

BASE=Path(__file__).resolve().parents[1]
ACCOUNT_ID="17841435427297631"
USERNAME="infinex_2025"
GRAPH="https://graph.facebook.com/v27.0/"
RAW="https://raw.githubusercontent.com/gsxrxx-spec/infinex-public-media/main/"
TZ=ZoneInfo("Europe/Madrid")
NOW=datetime.now(TZ)
DAY=NOW.date()
STAMP=DAY.isoformat()
LEDGER=BASE/"records"/(STAMP+"_09_reel.json")
MODE=sys.argv[1] if len(sys.argv)>1 else "publish"
if MODE not in ("publish","dry_run"):raise SystemExit(2)
CAPTIONS={
    "escaleras":(
        "Una escalera puede transformar el espacio y darle una personalidad única. 🟠\n\n"
        "En INFINEX trabajamos soluciones metálicas a medida para cada proyecto, "
        "con opciones de diseño, adaptación a las medidas y acabados elegidos.\n\n"
        "¿Te imaginas una escalera diferente en tu casa o negocio? Cuéntanos tu idea "
        "y pide presupuesto sin compromiso.\n\n"
        "🎬 Vídeo ilustrativo generado con IA. No muestra obras reales ejecutadas por INFINEX.\n\n"
        "#INFINEX #EscalerasMetalicas #EscalerasAMedida #Metalisteria"
    ),
    "puertas":(
        "Una entrada puede cambiar por completo el aspecto de tu casa. 🚪🟠\n\n"
        "Diseño, medidas personalizadas, materiales y acabados: en INFINEX "
        "estudiamos cada puerta metálica para encontrar una solución adaptada a tu espacio.\n\n"
        "¿Ya tienes una idea? Escríbenos y pide presupuesto sin compromiso.\n\n"
        "🎬 Vídeo ilustrativo generado con IA. No muestra trabajos reales de INFINEX.\n\n"
        "#INFINEX #PuertasMetalicas #PuertasAMedida #Metalisteria"
    ),
    "cerramientos":(
        "Un cerramiento puede aportar privacidad y transformar la entrada. 🟠\n\n"
        "Vallas, paneles y otras opciones metálicas de separación: "
        "en INFINEX estudiamos medidas, diseño y acabados según el espacio disponible.\n\n"
        "Cuéntanos lo que necesitas y pide presupuesto sin compromiso.\n\n"
        "🎬 Vídeo ilustrativo generado con IA. No representa una obra real de INFINEX.\n\n"
        "#INFINEX #CerramientosMetalicos #VallasMetalicas #Metalisteria"
    ),
    "soldadura":(
        "Detrás de una estructura metálica hay trabajo de precisión. 🟠\n\n"
        "Las uniones, los refuerzos y los acabados son esenciales en cada fabricación "
        "o adaptación de hierro. Cuéntanos qué necesitas en INFINEX.\n\n"
        "Solicita una valoración sin compromiso.\n\n"
        "🎬 Vídeo ilustrativo generado con IA. No muestra una obra real de INFINEX.\n\n"
        "#INFINEX #Soldadura #Hierro #Metalisteria"
    )
}

def log(*args):print(*args,flush=True)

def load_asset():
    manifests=list((BASE/"assets"/"reels").glob(STAMP+"_09_*/sources.json"))
    if len(manifests)!=1:
        raise RuntimeError("INFINEX_REEL_ASSET_NOT_PREAPPROVED_FOR_TODAY")
    manifest=json.loads(manifests[0].read_text(encoding="utf-8"))
    if (manifest.get("date")!=STAMP or manifest.get("slot")!="09" or
        manifest.get("type")!="REELS" or manifest.get("topic") not in TOPICS or
        manifest.get("illustrative_ai") is not True or
        manifest.get("approved_for_publish") is not True):
        raise RuntimeError("INFINEX_REEL_MANIFEST_NOT_APPROVED")
    item=str(manifest.get("video",""))
    if item.startswith("/") or "\\" in item or ".." in Path(item).parts or not item.endswith(".mp4"):
        raise RuntimeError("INFINEX_REEL_UNSAFE_ASSET")
    video=BASE/item
    if (not video.exists() or video.stat().st_size<200000 or
        hashlib.sha256(video.read_bytes()).hexdigest()!=manifest.get("video_sha256")):
        raise RuntimeError("INFINEX_REEL_VIDEO_INVALID")
    logo=BASE/"assets"/"branding"/"logo_infinex_original.jpg"
    if hashlib.sha256(logo.read_bytes()).hexdigest()!=manifest.get("logo_sha256"):
        raise RuntimeError("INFINEX_ORIGINAL_LOGO_MISMATCH")
    return manifest, video

def token():
    val=os.getenv("INFINEX_IG_TOKEN","").strip()
    if len(val)<50:raise RuntimeError("INFINEX_IG_TOKEN_MISSING")
    return val

def api(endpoint,form=None):
    request=urllib.request.Request(GRAPH+endpoint,
        data=urllib.parse.urlencode(form).encode("utf-8") if form is not None else None,
        headers={"Authorization":"Bearer "+token(),"User-Agent":"INFINEX-Reels-09/1.0"},
        method="POST" if form is not None else "GET")
    try:
        with urllib.request.urlopen(request,timeout=32) as response:return json.load(response)
    except urllib.error.HTTPError as e:
        # Never print credentials or Meta response body.
        raise RuntimeError("INFINEX_META_HTTP_"+str(e.code)) from None
    except (urllib.error.URLError,TimeoutError):
        raise RuntimeError("INFINEX_META_NETWORK_FAILURE") from None

def current_media():
    return api(ACCOUNT_ID+"/media?fields=id,caption,media_type,permalink,timestamp&limit=100").get("data",[])

def check_latest(topic):
    latest=api(ACCOUNT_ID+"/media?fields=id,caption,media_type,timestamp&limit=10").get("data")
    preceding=assert_not_consecutive(latest,topic)
    log("INFINEX_REEL_DISTINCT_TOPIC_OK",preceding or "account_empty",topic)

def save(state):
    LEDGER.parent.mkdir(exist_ok=True)
    temp=LEDGER.with_suffix(".tmp")
    temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,LEDGER)

def commit(message):
    subprocess.run(["git","config","user.name","INFINEX Scheduler"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","config","user.email","infinex-automation@users.noreply.github.com"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","add","--",str(LEDGER.relative_to(BASE))],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=BASE).returncode==0:return
    subprocess.run(["git","commit","-m",message],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","push","origin","HEAD:main"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)

def readback(media_id,caption):
    p=api(str(media_id)+"?fields=id,caption,media_type,media_product_type,permalink,timestamp")
    if (str(p.get("id"))!=str(media_id) or p.get("caption")!=caption or
        p.get("media_type")!="VIDEO" or
        p.get("media_product_type")!="REELS" or
        not p.get("permalink","").startswith("https://www.instagram.com/")):
        raise RuntimeError("INFINEX_REEL_READBACK_MISMATCH")
    return p

def public_video_verified(video,asset):
    req=urllib.request.Request(RAW+asset["video"],headers={"User-Agent":"INFINEX-Video-Readiness"})
    with urllib.request.urlopen(req,timeout=32) as response:
        payload=response.read()
    if hashlib.sha256(payload).hexdigest()!=asset["video_sha256"]:
        raise RuntimeError("INFINEX_REEL_PUBLIC_VIDEO_HASH_MISMATCH")
    return RAW+asset["video"]

def main():
    if MODE=="publish" and NOW.time()<dtime(9,0):
        log("INFINEX_REEL_NOT_DUE_YET");return
    asset,video=load_asset()
    caption=CAPTIONS[asset["topic"]]
    if MODE=="dry_run":
        log("INFINEX_REEL_DRY_RUN_OK",STAMP,asset["topic"],video.stat().st_size)
        return
    identity=api(ACCOUNT_ID+"?fields=id,username")
    if str(identity.get("id"))!=ACCOUNT_ID or identity.get("username")!=USERNAME:
        raise RuntimeError("INFINEX_REEL_WRONG_ACCOUNT")
    state=json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    if state.get("status") in ("REJECTED_BY_USER","DO_NOT_REPOST") or state.get("do_not_republish"):
        log("INFINEX_REEL_USER_REJECTED");return
    for item in current_media():
        if item.get("caption")==caption:
            verified=readback(item["id"],caption)
            state.update({"status":"PUBLISHED_VERIFIED","media_id":str(item["id"]),
                          "permalink":verified["permalink"],"topic":asset["topic"],"date":STAMP})
            save(state);commit("INFINEX reconcile morning reel "+STAMP)
            log("INFINEX_REEL_ALREADY_PUBLISHED_VERIFIED",verified["permalink"]);return
    if state.get("status")=="PUBLISHED_VERIFIED":
        raise RuntimeError("INFINEX_REEL_DELETED_NO_AUTOREPOST")
    if state.get("publish_attempt_started") or state.get("creation_id"):
        raise RuntimeError("INFINEX_REEL_UNCERTAIN_ATTEMPT_NO_RETRY")
    check_latest(asset["topic"])
    url=public_video_verified(video,asset)
    state={"status":"PREPARED","date":STAMP,"slot":"09","topic":asset["topic"],
           "caption_sha256":hashlib.sha256(caption.encode()).hexdigest(),
           "video_sha256":asset["video_sha256"],"publish_attempt_started":False}
    save(state);commit("INFINEX reserve safe morning reel "+STAMP)
    try:
        creation=api(ACCOUNT_ID+"/media",{
            "media_type":"REELS","video_url":url,"caption":caption,"share_to_feed":"true"})
        cid=str(creation.get("id",""))
        if not cid.isdigit():raise RuntimeError("INFINEX_REEL_CREATE_NO_ID")
        state["creation_id"]=cid;state["status"]="CONTAINER_CREATED";save(state);commit("INFINEX reel container "+STAMP)
        ready=False
        for i in range(35):
            status=api(cid+"?fields=status_code").get("status_code")
            if status=="FINISHED":ready=True;break
            if status in ("ERROR","EXPIRED"):raise RuntimeError("INFINEX_REEL_CONTAINER_FAILED")
            time.sleep(8)
        if not ready:raise RuntimeError("INFINEX_REEL_CONTAINER_NOT_READY")
        check_latest(asset["topic"])
        state["publish_attempt_started"]=True
        state["status"]="PUBLISHING_UNCERTAIN_DO_NOT_RETRY";save(state)
        commit("INFINEX reserve irreversible reel publish "+STAMP)
        published=api(ACCOUNT_ID+"/media_publish",{"creation_id":cid})
        media_id=str(published.get("id",""))
        if not media_id.isdigit():raise RuntimeError("INFINEX_REEL_NO_MEDIA_ID")
        state["media_id"]=media_id;state["status"]="PUBLISH_SENT_VERIFY_PENDING";save(state)
        for i in range(8):
            try:
                post=readback(media_id,caption)
                state.update({"status":"PUBLISHED_VERIFIED","permalink":post["permalink"],
                              "timestamp":post.get("timestamp")})
                save(state);commit("INFINEX reel verified "+STAMP)
                log("INFINEX_REEL_PUBLISHED_VERIFIED",post["permalink"],asset["topic"])
                return
            except RuntimeError:
                time.sleep(4)
        commit("INFINEX reel readback pending "+STAMP)
        raise RuntimeError("INFINEX_REEL_SENT_READBACK_PENDING")
    except Exception as e:
        state["error_code"]=str(e)[:100]
        if not state.get("publish_attempt_started"):
            state["status"]="FAILED_BEFORE_PUBLISH_REVIEW_REQUIRED"
        save(state)
        try:commit("INFINEX reel failure record "+STAMP)
        except Exception:pass
        raise

if __name__=="__main__":
    try:main()
    except Exception as e:
        log("INFINEX_REEL_ERROR",str(e)[:110])
        raise SystemExit(1)
