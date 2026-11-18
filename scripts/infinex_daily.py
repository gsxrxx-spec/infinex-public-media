#!/usr/bin/env python3
"""INFINEX: two carousels daily at 09 and 17 Europe/Madrid without duplicate retries."""
from __future__ import annotations
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE = Path(__file__).resolve().parents[1]
IG_ID = "17841435427297631"
IG_USERNAME = "infinex_2025"
GRAPH = "https://graph.facebook.com/v27.0/"
RAW = "https://raw.githubusercontent.com/gsxrxx-spec/infinex-public-media/main/"
TZ = ZoneInfo("Europe/Madrid")
LOGO = BASE / "assets/branding/logo_infinex_original.jpg"
LOGO_SHA256 = "65e35a825681bad432082014a8b69402d30996be58b3ae97958deb3a40d33f31"
BANK = BASE / "assets/photo_library.json"
BLACK = (7,10,13)
ORANGE = (255,112,15)
WHITE = (245,246,248)
GRAY = (178,181,185)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Only the internal recovery process uses INFINEX_BACKFILL_DATE for publishing.
IS_DRY_RUN = len(sys.argv)>1 and sys.argv[1]=="dry_run"
TODAY = datetime.now(TZ).date()
DATE = (date.fromisoformat(os.environ["INFINEX_DRYRUN_DATE"])
        if IS_DRY_RUN and os.getenv("INFINEX_DRYRUN_DATE")
        else date.fromisoformat(os.environ["INFINEX_BACKFILL_DATE"])
        if not IS_DRY_RUN and os.getenv("INFINEX_BACKFILL_DATE")
        else TODAY)
if not IS_DRY_RUN and sys.argv[1:2]!=["recover"] and (DATE>TODAY or DATE<date(2026,11,19) or (TODAY-DATE).days>30):
    raise RuntimeError("PUBLICATION_DATE_OUTSIDE_RECOVERY_WINDOW")
DAY_KEY = DATE.isoformat()
SLOT = os.getenv("INFINEX_SLOT","09")
if SLOT not in ("09","17"):
    raise RuntimeError("INVALID_PUBLICATION_SLOT")
SLOT_TIME = SLOT + ":00"
MEDIA_DIR = BASE / "assets/daily" / DAY_KEY / SLOT
RECORD_FILE = BASE / "records" / (DAY_KEY+"_"+SLOT+".json")
REVIEW_TAG = "INFINEX-DIARIO-" + DATE.strftime("%Y%m%d") + "-" + SLOT

def log(*parts):
    print(*parts,flush=True)

def atomic_record(state):
    RECORD_FILE.parent.mkdir(parents=True,exist_ok=True)
    temp=RECORD_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,RECORD_FILE)

def commit(paths,message):
    subprocess.run(["git","config","user.name","INFINEX Scheduler"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","config","user.email","infinex-automation@users.noreply.github.com"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","add","--",*paths],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    status=subprocess.run(["git","diff","--cached","--quiet"],cwd=BASE)
    if status.returncode==0:
        return
    subprocess.run(["git","commit","-m",message],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","push","origin","HEAD:main"],cwd=BASE,check=True,stdout=subprocess.DEVNULL)
    log("LEDGER_COMMIT_OK",message)

def source_url(photo):
    return ("https://images.pexels.com/photos/{0}/pexels-photo-{0}.jpeg?"
            "auto=compress&cs=tinysrgb&w=2000").format(photo["id"])

def download_photo(photo):
    assert photo["page"].startswith("https://www.pexels.com/photo/")
    assert photo["page"].rstrip("/").endswith("-"+str(photo["id"]))
    req=urllib.request.Request(source_url(photo),headers={"User-Agent":"INFINEX-Licensed-Photo/1.0"})
    with urllib.request.urlopen(req,timeout=35) as r:
        content=r.read()
        content_type=r.headers.get("Content-Type","")
    if len(content)<45000 or "image/" not in content_type:
        raise RuntimeError("STOCK_IMAGE_MISSING_OR_INVALID")
    photo_image=Image.open(io.BytesIO(content)).convert("RGB")
    if min(photo_image.size)<650:
        raise RuntimeError("STOCK_IMAGE_TOO_SMALL")
    return photo_image

def font(size,bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR,size)

def photo_selection():
    data=json.loads(BANK.read_text(encoding="utf-8"))
    if data.get("license")!="https://www.pexels.com/license/":
        raise RuntimeError("UNVERIFIED_IMAGE_LICENSE")
    epoch=(DATE-date(2026,11,18)).days
    if epoch<0:
        raise RuntimeError("DATE_BEFORE_START")
    groups=("welding","gates","structures")
    # Distinct morning/evening photo selection: 2 editions per day.
    edition = epoch*2+(0 if SLOT=="09" else 1)
    rotation=edition%3
    output=[]
    for index in range(3):
        group=groups[(index+rotation)%3]
        candidates=data[group]
        offset=(edition//3 + index*2)%len(candidates)
        output.append((group,candidates[offset]))
    return output

def caption_for(chosen):
    text={
        "welding":"Soldadura y hierro",
        "gates":"Puertas y vallas",
        "structures":"Estructuras metálicas",
    }
    titles=" · ".join(text[g] for g,p in chosen)
    return ("INFINEX | Ideas en hierro. Soluciones reales. 🟠\n\n"+
            titles+".\n\n"
            "Exploramos diferentes aplicaciones del metal, desde el trabajo del hierro "
            "hasta cerramientos y estructuras. INFINEX trabaja en estructuras, hierro, "
            "automatismos y rehabilitación.\n\n"
            "📷 Fotografías ilustrativas de archivo (Pexels). No son obras ejecutadas "
            "por INFINEX.\n\n"
            "#INFINEX #Metalisteria #EstructurasMetalicas #Hierro #Automatismos\n\n"
            + "📅 " + DATE.strftime("%d/%m/%Y") + " · " + SLOT_TIME)

def render_slide(photo_image,category,number,out):
    if hashlib.sha256(LOGO.read_bytes()).hexdigest()!=LOGO_SHA256:
        raise RuntimeError("INFINEX_LOGO_CHANGED")
    logo=Image.open(LOGO).convert("RGB")
    logo=ImageOps.contain(logo,(210,210),Image.Resampling.LANCZOS)
    W,H=1080,1350
    canvas=Image.new("RGB",(W,H),BLACK)
    hero=ImageOps.fit(photo_image,(W,1000),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
    canvas.paste(hero,(0,0))
    fade=Image.new("RGBA",(W,H),(0,0,0,0))
    fd=ImageDraw.Draw(fade)
    for y in range(660,1015):
        alpha=max(0,min(255,int((y-660)*255/355)))
        fd.line((0,y,W,y),fill=(0,0,0,alpha))
    canvas=Image.alpha_composite(canvas.convert("RGBA"),fade).convert("RGB")
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,W,13),fill=ORANGE)
    d.rounded_rectangle((40,42,50+logo.width+10,52+logo.height+10),radius=20,fill=(6,8,10))
    canvas.paste(logo,(50,52))
    d=ImageDraw.Draw(canvas)
    labels={
        "welding":("SOLDADURA Y HIERRO","El metal cobra forma"),
        "gates":("PUERTAS Y VALLAS","Cerramientos y diseño"),
        "structures":("ESTRUCTURAS METÁLICAS","Función y arquitectura")
    }
    title,sub=labels[category]
    d.text((870,82),f"{number:02d} / 03",font=font(29,True),fill=WHITE,stroke_width=1,stroke_fill=BLACK)
    d.rectangle((60,952,212,964),fill=ORANGE)
    size=64
    while d.textbbox((0,0),title,font=font(size,True))[2]>W-110: size-=2
    d.text((60,1023),title,font=font(size,True),fill=WHITE)
    d.text((62,1122),sub,font=font(35),fill=(218,220,221))
    d.line((60,1200,1020,1200),fill=(71,76,79),width=2)
    d.text((60,1230),"INFINEX  ·  IDEAS EN HIERRO",font=font(27,True),fill=ORANGE)
    d.text((60,1292),"Fotografía ilustrativa · Pexels",font=font(19),fill=GRAY)
    canvas.save(out,"JPEG",quality=92,subsampling=0,optimize=True)

def build():
    chosen=photo_selection()
    if not LOGO.exists(): raise RuntimeError("LOGO_NOT_FOUND")
    MEDIA_DIR.mkdir(parents=True,exist_ok=True)
    manifest={"date":DAY_KEY,"slot":SLOT,"destination":IG_USERNAME,"license":"https://www.pexels.com/license/",
              "not_actual_infinex_works":True,"sources":[],"images":[]}
    for i,(category,photo) in enumerate(chosen,1):
        image=download_photo(photo)
        out=MEDIA_DIR/f"{i:02}.jpg"
        render_slide(image,category,i,out)
        if out.stat().st_size<50000:raise RuntimeError("JPG_TOO_SMALL")
        manifest["sources"].append({"id":photo["id"],"category":category,
                                     "page":photo["page"],"author":photo.get("author","Pexels")})
        manifest["images"].append({"path":str(out.relative_to(BASE)).replace("\\","/"),
                                    "sha256":hashlib.sha256(out.read_bytes()).hexdigest()})
    (MEDIA_DIR/"sources.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return chosen,manifest

def review_before_publish(chosen,manifest,caption):
    """Automated preflight: correct brand, approved text, unique licensed photos and dimensions."""
    expected_groups={"welding","gates","structures"}
    if len(chosen)!=3 or {g for g,p in chosen}!=expected_groups:
        raise RuntimeError("CONTENT_CATEGORIES_NOT_APPROVED")
    if len({str(p["id"]) for g,p in chosen})!=3:
        raise RuntimeError("CONTENT_REPEATED_PHOTO")
    if (len(manifest.get("images",[]))!=3 or len(manifest.get("sources",[]))!=3 or
        manifest.get("license")!="https://www.pexels.com/license/" or
        manifest.get("not_actual_infinex_works") is not True):
        raise RuntimeError("CONTENT_LICENSE_OR_MANIFEST_INVALID")
    if (caption!=caption_for(chosen) or
        "No son obras ejecutadas por INFINEX." not in caption or
        "#INFINEX" not in caption):
        raise RuntimeError("CONTENT_CAPTION_INVALID")
    if hashlib.sha256(LOGO.read_bytes()).hexdigest()!=LOGO_SHA256:
        raise RuntimeError("CONTENT_CORPORATE_LOGO_INVALID")
    for item,(_,photo) in zip(manifest["images"],chosen):
        if item["path"].startswith("/") or ".." in Path(item["path"]).parts:
            raise RuntimeError("CONTENT_IMAGE_UNSAFE_PATH")
        f=BASE/item["path"]
        if (not f.is_file() or f.stat().st_size<50000 or
            hashlib.sha256(f.read_bytes()).hexdigest()!=item["sha256"]):
            raise RuntimeError("CONTENT_IMAGE_INTEGRITY_FAILED")
        with Image.open(f) as img:
            if img.format!="JPEG" or img.size!=(1080,1350):
                raise RuntimeError("CONTENT_IMAGE_DIMENSIONS_INVALID")
        if not str(photo["page"]).startswith("https://www.pexels.com/photo/"):
            raise RuntimeError("CONTENT_IMAGE_SOURCE_INVALID")
    log("CONTENT_REVIEW_PASSED","date",DAY_KEY,"slot",SLOT,
        "images",3,"logo","original","stock","illustrative")

def token():
    t=os.getenv("INFINEX_IG_TOKEN","").strip()
    if len(t)<50:raise RuntimeError("META_SECRET_NOT_CONFIGURED")
    return t

def api(endpoint,method="GET",fields=None):
    tok=token()
    body=urllib.parse.urlencode(fields).encode("utf-8") if method=="POST" else None
    url=GRAPH+endpoint
    req=urllib.request.Request(url,data=body,method=method,headers={
        "Authorization":"Bearer "+tok,"User-Agent":"INFINEX-Daily/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=24) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        # Nunca mostrar un URL ni respuesta que pueda contener credenciales.
        raise RuntimeError(f"META_HTTP_{e.code}") from None
    except (urllib.error.URLError,TimeoutError):
        raise RuntimeError("META_NETWORK_FAILURE") from None

def preflight():
    identity=api(IG_ID+"?fields=id,username")
    if str(identity.get("id"))!=IG_ID or identity.get("username")!=IG_USERNAME:
        raise RuntimeError("IG_IDENTITY_MISMATCH")
    return True

def public_images_are_ready(manifest):
    for data in manifest["images"]:
        url=RAW+data["path"]
        passed=False
        for wait in (0,2,4,6,8):
            if wait:time.sleep(wait)
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"INFINEX-Asset-Integrity"})
                with urllib.request.urlopen(req,timeout=14) as r:
                    remote=r.read()
                    typ=r.headers.get("Content-Type","")
                if "image/" in typ and hashlib.sha256(remote).hexdigest()==data["sha256"]:
                    passed=True
                    break
            except Exception:
                pass
        if not passed: raise RuntimeError("PUBLIC_IMAGE_UNAVAILABLE")
    return True

def status_code(creation_id):
    last=None
    for i in range(8):
        last=api(str(creation_id)+"?fields=status_code").get("status_code")
        if last=="FINISHED":return True
        if last in ("ERROR","EXPIRED"):return False
        time.sleep(3)
    raise RuntimeError("META_CONTAINER_NOT_READY_"+str(last))

def get_post(media_id):
    return api(str(media_id)+"?fields=id,media_type,permalink,caption,timestamp,children{id,media_type}")

def verify_post(media_id,expected_caption):
    post=get_post(media_id)
    children=post.get("children",{}).get("data",[])
    if (str(post.get("id"))!=str(media_id) or post.get("media_type")!="CAROUSEL_ALBUM" or
        post.get("caption")!=expected_caption or len(children)!=3 or
        not str(post.get("permalink","")).startswith("https://www.instagram.com/")):
        raise RuntimeError("POST_READBACK_MISMATCH")
    return post

def find_today(caption):
    for item in api(IG_ID+"/media?fields=id,caption,media_type,permalink&limit=100").get("data",[]):
        if item.get("caption")==caption:
            return item
    return None

def dry_run():
    preflight()
    chosen,manifest=build()
    review_before_publish(chosen,manifest,caption_for(chosen))
    log("DRY_RUN_OK","date",DAY_KEY,"slot",SLOT,"images",len(manifest["images"]))
    log("SAFETY","NO_POST","NO_COMMIT","TOKEN_NOT_PRINTED")
    for source in manifest["sources"]:log("LICENSED_SOURCE",source["page"])

def publish():
    preflight()
    chosen=photo_selection()
    expected_caption=caption_for(chosen)
    previous=(json.loads(RECORD_FILE.read_text(encoding="utf-8"))
              if RECORD_FILE.exists() else None)
    if previous and previous.get("status")=="PUBLISHED_VERIFIED":
        log("SKIPPED_ALREADY_VERIFIED",DAY_KEY,SLOT,previous.get("permalink",""))
        return
    # Reconcile from Instagram before any new publish, including after crashes.
    found=find_today(expected_caption)
    if found:
        post=verify_post(found["id"],expected_caption)
        state=previous or {"date":DAY_KEY,"slot":SLOT,"target":IG_USERNAME,
                           "account_id":IG_ID,"caption":expected_caption}
        state.update({"status":"PUBLISHED_VERIFIED","media_id":str(post["id"]),
                      "permalink":post["permalink"],"timestamp":post.get("timestamp")})
        atomic_record(state)
        commit([str(RECORD_FILE.relative_to(BASE))],
               "INFINEX reconciled IG post "+DAY_KEY+" "+SLOT)
        log("RECONCILED_PUBLISHED_VERIFIED",post["permalink"])
        return
    if previous:
        if (previous.get("publish_attempt_started") or previous.get("media_id") or
            previous.get("status") in ("PUBLISHING_RESULT_UNCERTAIN_NO_RETRY",
                                       "PUBLISH_SENT_NOT_VERIFIED")):
            # An uncertain media_publish must NEVER be resent blindly.
            log("BLOCKED_UNCERTAIN_POST_NO_DUPLICATE",DAY_KEY,SLOT)
            raise RuntimeError("UNCONFIRMED_META_PUBLISH_NO_AUTOMATIC_RETRY")
        log("RESUMING_SAFE_PRE_PUBLISH_FAILURE",DAY_KEY,SLOT)
    chosen,manifest=build()
    review_before_publish(chosen,manifest,expected_caption)
    state={"date":DAY_KEY,"slot":SLOT,"target":IG_USERNAME,"account_id":IG_ID,
           "status":"CLAIMED_NO_RETRY","caption":expected_caption,
           "images":manifest["images"],"media_id":None,"children":[],"creation_id":None,
           "publish_attempt_started":False,
           "attempt_count":(previous or {}).get("attempt_count",0)+1,
           "source":"Pexels; illustrative photos, not INFINEX jobs"}
    atomic_record(state)
    commit([str(RECORD_FILE.relative_to(BASE)),str(MEDIA_DIR.relative_to(BASE))],
           "INFINEX reserve daily IG post "+DAY_KEY+" "+SLOT)
    # La reserva ya se ha confirmado en Git: si falla algo, no repetir POST sin leer Meta.
    try:
        public_images_are_ready(manifest)
        for data in manifest["images"]:
            creation=api(IG_ID+"/media","POST",{
                "image_url":RAW+data["path"],"is_carousel_item":"true"})
            child_id=str(creation["id"])
            state["children"].append(child_id)
            atomic_record(state)
            if not status_code(child_id):raise RuntimeError("META_CHILD_FAILED")
        parent=api(IG_ID+"/media","POST",{
            "media_type":"CAROUSEL",
            "children":",".join(state["children"]),
            "caption":expected_caption})
        state["creation_id"]=str(parent["id"])
        atomic_record(state)
        if not status_code(state["creation_id"]):raise RuntimeError("META_PARENT_FAILED")
        state["publish_attempt_started"]=True
        state["status"]="PUBLISHING_RESULT_UNCERTAIN_NO_RETRY"
        atomic_record(state)
        commit([str(RECORD_FILE.relative_to(BASE))],"INFINEX publish attempt reserved "+DAY_KEY+" "+SLOT)
        # ÚNICA solicitud real; nunca hacer segundo POST ante un timeout.
        published=api(IG_ID+"/media_publish","POST",{"creation_id":state["creation_id"]})
        state["media_id"]=str(published["id"])
        state["status"]="PUBLISH_SENT_NOT_VERIFIED"
        atomic_record(state)
        for i in range(5):
            try:
                post=verify_post(state["media_id"],expected_caption)
                state["status"]="PUBLISHED_VERIFIED"
                state["permalink"]=post["permalink"]
                state["timestamp"]=post.get("timestamp")
                atomic_record(state)
                commit([str(RECORD_FILE.relative_to(BASE))],"INFINEX verified IG post "+DAY_KEY+" "+SLOT)
                log("PUBLISHED_VERIFIED",post["permalink"],"child_count",3)
                return
            except RuntimeError:
                time.sleep(3)
        commit([str(RECORD_FILE.relative_to(BASE))],"INFINEX pending readback "+DAY_KEY+" "+SLOT)
        raise RuntimeError("POST_SENT_BUT_READBACK_PENDING")
    except Exception as e:
        state["error_code"]=str(e)[:80]
        if state["status"]=="CLAIMED_NO_RETRY":
            state["status"]="PRE_PUBLISH_FAILED_NO_AUTOMATIC_RETRY"
        atomic_record(state)
        try:commit([str(RECORD_FILE.relative_to(BASE))],"INFINEX error state "+DAY_KEY+" "+SLOT)
        except Exception:pass
        raise

def verify():
    preflight()
    if not RECORD_FILE.exists():
        log("REVIEW_NO_PUBLICATION_RECORD",DAY_KEY,"slot",SLOT)
        raise RuntimeError("REVIEW_MISSING_PUBLICATION_RECORD")
    state=json.loads(RECORD_FILE.read_text(encoding="utf-8"))
    caption=state["caption"]
    media_id=state.get("media_id")
    if not media_id:
        found=find_today(caption)
        if found:media_id=str(found.get("id"))
    if not media_id:
        raise RuntimeError("REVIEW_UNVERIFIED_NO_REPOST")
    post=verify_post(media_id,caption)
    state["status"]="PUBLISHED_VERIFIED"
    state["media_id"]=str(media_id)
    state["permalink"]=post["permalink"]
    state["timestamp"]=post.get("timestamp")
    state["reviewed_at"]=datetime.now(TZ).isoformat()
    atomic_record(state)
    commit([str(RECORD_FILE.relative_to(BASE))],"INFINEX review "+SLOT+":15 "+DAY_KEY)
    log("INDEPENDENT_REVIEW_VERIFIED",DAY_KEY,SLOT,post["permalink"])

def run_recovery_task(mode,day,slot):
    env=os.environ.copy()
    env["INFINEX_BACKFILL_DATE"]=day.isoformat()
    env["INFINEX_SLOT"]=slot
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),mode],
                          cwd=BASE,env=env,check=False,timeout=650)
    log("RECOVERY_TASK",day.isoformat(),slot,mode,
        "OK" if result.returncode==0 else "FAILED")
    return result.returncode==0

def recover():
    """Recheck due slots every scheduled run; publish late when safe, never duplicate uncertain posts."""
    now=datetime.now(TZ)
    max_publications=2
    max_reviews=4
    attempted_publications=0
    attempted_reviews=0
    errors_today=[]
    start_day=date(2026,11,19)
    # Most recent first: today's two slots always have priority over the backlog.
    for days_ago in range(31):
        day=now.date()-timedelta(days=days_ago)
        if day<start_day:
            break
        for slot in ("09","17"):
            due=datetime.combine(day,dtime(int(slot),0),tzinfo=TZ)
            if now<due:
                continue
            ledger=BASE/"records"/(day.isoformat()+"_"+slot+".json")
            state=None
            if ledger.is_file():
                try:state=json.loads(ledger.read_text(encoding="utf-8"))
                except Exception:
                    log("RECOVERY_INVALID_LEDGER",day.isoformat(),slot)
                    if day==now.date():errors_today.append(slot+"_invalid_ledger")
                    continue
            if state and state.get("status")=="PUBLISHED_VERIFIED":
                if (now>=due+timedelta(minutes=15) and
                    not state.get("reviewed_at") and attempted_reviews<max_reviews):
                    attempted_reviews+=1
                    if not run_recovery_task("verify",day,slot) and day==now.date():
                        errors_today.append(slot+"_review")
                continue
            if state and (state.get("publish_attempt_started") or
                          state.get("status") in ("PUBLISHING_RESULT_UNCERTAIN_NO_RETRY",
                                                  "PUBLISH_SENT_NOT_VERIFIED")):
                # A read-only reconciliation, never blindly resend the POST.
                if attempted_reviews<max_reviews:
                    attempted_reviews+=1
                    if not run_recovery_task("verify",day,slot) and day==now.date():
                        errors_today.append(slot+"_uncertain")
                continue
            if attempted_publications<max_publications:
                attempted_publications+=1
                if not run_recovery_task("publish",day,slot) and day==now.date():
                    errors_today.append(slot+"_publish")
    log("RECOVERY_SCAN_DONE","posts_attempted",attempted_publications,
        "reviews_attempted",attempted_reviews,"today_errors",len(errors_today))
    if errors_today:
        raise RuntimeError("RECOVERY_INCOMPLETE_TODAY_"+",".join(errors_today))

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "dry_run"
    if mode not in ("dry_run","publish","verify","recover"):
        raise SystemExit(2)
    if mode=="dry_run":dry_run()
    elif mode=="publish":publish()
    elif mode=="verify":verify()
    else:recover()

if __name__=="__main__":
    try:main()
    except Exception as exc:
        # Registro seguro, sin token ni datos de acceso.
        log("INFINEX_PROCESS_ERROR",str(exc)[:120])
        sys.exit(1)
