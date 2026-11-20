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
from infinex_editorial_policy import TOPICS, assert_not_consecutive, topic_from_caption
from infinex_autorepair import alternate_topics, unique_headlines
from infinex_weekly_plan import START_DATE, is_scheduled
from infinex_carousel_quality import (REGISTRY,headings_for,validate_headings,
    used_photos,ensure_unique,reserve,confirmed_reserved,
    file_image_signature,hamming)

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

TOPIC_ROTATION = TOPICS
EDITORIAL_THEME = None
EDITORIAL_TITLES = None

# Dos datos practicos por diapositiva, sin mezclar servicios ni saturar diseño.
SLIDE_DETAILS = {
    "puertas": (
        ("Opciones lisas, de lamas o a medida", "Privacidad y estilo para tu entrada"),
        ("Hierro, chapa o aluminio según proyecto", "Medidas y acabados personalizados"),
        ("Enséñanos la entrada y tus preferencias", "Solicita presupuesto sin compromiso"),
    ),
    "escaleras": (
        ("Para interiores o zonas exteriores", "Diseño adaptado al espacio disponible"),
        ("Tramos rectos o con giro según hueco", "Barandillas y acabados a elegir"),
        ("Comparte medidas, fotos y tu idea", "Valora opciones sin compromiso"),
    ),
    "cerramientos": (
        ("Para patios, entradas y jardines", "Delimita sin renunciar al estilo"),
        ("Opciones de privacidad y acabados", "Medidas ajustadas a cada espacio"),
        ("Cuéntanos longitud, altura y diseño", "Pide presupuesto sin compromiso"),
    ),
    "soldadura": (
        ("Uniones, refuerzos y adaptaciones", "Soluciones para piezas metálicas"),
        ("Cada unión responde a un uso", "Revisamos necesidades y acabados"),
        ("Comparte una foto y tu idea", "Solicita valoración sin compromiso"),
    ),
}

def topic_for_slot():
    if EDITORIAL_THEME is not None:
        return EDITORIAL_THEME
    epoch = (DATE-date(2026,11,19)).days
    if epoch < 0: raise RuntimeError("DATE_BEFORE_EDITORIAL_START")
    edition = epoch*2 + (0 if SLOT=="09" else 1)
    intended = TOPIC_ROTATION[edition % len(TOPIC_ROTATION)]
    # If the other slot is an approved Reel, do not visually repeat its topic.
    other="17" if SLOT=="09" else "09"
    if DATE>=START_DATE and is_scheduled(DATE,other,"reel"):
        manifests=list((BASE/"assets"/"reels").glob(
            DATE.isoformat()+"_"+other+"_*/sources.json"))
        approved=[]
        for path in manifests:
            candidate=json.loads(path.read_text(encoding="utf-8"))
            if candidate.get("approved_for_publish") is True:
                approved.append(candidate.get("topic"))
        if len(approved)>1:
            raise RuntimeError("EDITORIAL_MULTIPLE_REEL_ASSETS_SAME_SLOT")
        if approved and intended==approved[0]:
            intended=TOPIC_ROTATION[(edition+1)%len(TOPIC_ROTATION)]
    return intended

def photo_candidates(theme):
    """Return all eligible fresh licensed sources, for replacement retries."""
    data=json.loads(BANK.read_text(encoding="utf-8"))
    if data.get("license")!="https://www.pexels.com/license/":
        raise RuntimeError("UNVERIFIED_IMAGE_LICENSE")
    groups={"puertas":"gates","escaleras":"structures",
            "cerramientos":"gates","soldadura":"welding"}
    group=groups[theme]
    used,_,_,_=used_photos(BASE,exclude=MEDIA_DIR/"sources.json")
    candidates=[p for p in data[group]
                if str(p["id"]) not in used and not any(
                    word in (p.get("page","")+" "+p.get("title","")).lower()
                    for word in ("rusty","creepy","deteriorated","damaged","broken","abandoned"))]
    # Rotate candidates but keep the entire approved pool available if an
    # individual photo turns out unsuitable or cannot be downloaded.
    if not candidates:
        return []
    edition=(DATE-date(2026,11,19)).days*2 + (0 if SLOT=="09" else 1)
    offset=(edition//len(TOPIC_ROTATION))%len(candidates)
    return [(group,candidates[(offset+i)%len(candidates)])
            for i in range(len(candidates))]

def photo_selection():
    selected=photo_candidates(topic_for_slot())
    if len(selected)<3:
        raise RuntimeError("EDITORIAL_NEEDS_MORE_NEW_PHOTOS_"+topic_for_slot().upper())
    return selected[:3]

def prepare_editorial_plan(previous_topic=None,skip_topics=()):
    """Search another topic/copy before accepting an editorial failure.

    All candidates must still be unused, Pexels-licensed, and on topic.
    Existing Meta publish attempts must never enter this regeneration path.
    """
    global EDITORIAL_THEME,EDITORIAL_TITLES
    EDITORIAL_THEME=None
    desired=topic_for_slot()
    edition=(DATE-date(2026,11,19)).days*2+(0 if SLOT=="09" else 1)
    _,historic_titles,_,_=used_photos(BASE,exclude=MEDIA_DIR/"sources.json")
    for theme in alternate_topics(desired,previous_topic):
        if theme in skip_topics:continue
        EDITORIAL_THEME=theme
        try:
            if len(photo_candidates(theme))<3:
                log("EDITORIAL_TRY_ANOTHER_TOPIC_NO_NEW_PHOTOS",theme)
                continue
            titles=unique_headlines(theme,edition,historic_titles)
            EDITORIAL_TITLES=tuple(titles)
            log("EDITORIAL_REPLACEMENT_READY",theme,"new_photo_options",
                len(photo_candidates(theme)),"headlines",3)
            return
        except RuntimeError as exc:
            log("EDITORIAL_REJECTED_RETRY_NEXT_TOPIC",theme,str(exc)[:85])
    EDITORIAL_THEME=None
    EDITORIAL_TITLES=None
    raise RuntimeError("EDITORIAL_REPLENISH_LICENSED_PHOTOS_BEFORE_PUBLISHING")

def caption_for(chosen):
    # Cada carrusel vende un servicio concreto y termina con una acción.
    copy={
        "puertas":(
            "¿Y si tu entrada tuviera el diseño que siempre has imaginado? 🚪🔶\n\n"
            "Una puerta puede dar personalidad a toda una fachada. En INFINEX trabajamos "
            "puertas metálicas a medida: de chapa, reforzadas, de aluminio y diseños "
            "personalizados según el espacio y el estilo que buscas.\n\n"
            "¿Te imaginas estrenando puerta? Escríbenos y pide presupuesto sin compromiso.\n\n"
            "#INFINEX #PuertasMetalicas #PuertasAMedida #Metalisteria"),
        "escaleras":(
            "¿Y si esa escalera aprovechara mejor el espacio y además se convirtiera "
            "en uno de los detalles favoritos de tu casa? 🔶\n\n"
            "En INFINEX realizamos escaleras metálicas a medida para adaptarlas "
            "a cada hueco, recorrido y estilo. Acabados a tu gusto y soluciones "
            "personalizadas, para interior o exterior según tu proyecto.\n\n"
            "Cuéntanos cómo imaginas tu escalera y pide presupuesto sin compromiso.\n\n"
            "#INFINEX #EscalerasMetalicas #EscalerasAMedida #Metalisteria"),
        "cerramientos":(
            "Tu entrada y tu espacio exterior pueden ganar personalidad con un "
            "cerramiento metálico pensado para ti. 🔶\n\n"
            "¿Prefieres más privacidad, líneas modernas o un diseño clásico? "
            "En INFINEX trabajamos vallas y cerramientos metálicos a medida, "
            "adaptados al espacio y al acabado que quieras.\n\n"
            "Escríbenos, enséñanos tu idea y pide presupuesto sin compromiso.\n\n"
            "#INFINEX #CerramientosMetalicos #VallasMetalicas #Metalisteria"),
        "soldadura":(
            "¿Tienes una pieza de hierro que necesitas reparar, reforzar o adaptar? 🔶\n\n"
            "A veces no necesitas sustituirlo todo: necesitas una solución metálica "
            "bien pensada para el uso real. En INFINEX trabajamos el hierro y "
            "la soldadura en proyectos a medida.\n\n"
            "Cuéntanos qué necesitas y pide presupuesto sin compromiso.\n\n"
            "#INFINEX #Soldadura #Hierro #FabricacionMetalica"),
    }
    theme=topic_for_slot()
    return ("INFINEX | Ideas en hierro. Soluciones reales. 🟠\n\n"
            +copy[theme]
            +"\n\n📷 Fotografías ilustrativas de archivo (Pexels). No son obras ejecutadas por INFINEX."
            +"\n\n📅 "+DATE.strftime("%d/%m/%Y")+" · "+SLOT_TIME)

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
    subtitles={
        "puertas":("Una entrada a tu manera","Cada acabado cuenta","Cuéntanos qué buscas"),
        "escaleras":("Diseño para tu espacio","Medidas que encajan","Convirtamos tu idea en realidad"),
        "cerramientos":("Otra forma de dar privacidad","Materiales y acabado a elegir","Una solución para tu exterior"),
        "soldadura":("Trabajo pensado para ti","Repara, refuerza o adapta","Cada proyecto es diferente"),
    }
    edition=(DATE-date(2026,11,19)).days*2+(0 if SLOT=="09" else 1)
    title=(EDITORIAL_TITLES or headings_for(topic_for_slot(),edition))[number-1]
    sub=subtitles[topic_for_slot()][number-1]
    d.text((870,82),f"{number:02d} / 03",font=font(29,True),fill=WHITE,stroke_width=1,stroke_fill=BLACK)
    d.rectangle((60,952,212,964),fill=ORANGE)
    size=64
    while d.textbbox((0,0),title,font=font(size,True))[2]>W-110: size-=2
    d.text((60,1023),title,font=font(size,True),fill=WHITE)
    d.text((62,1112),sub,font=font(34),fill=(218,220,221))
    # Dos detalles practicos diferentes para cada pagina.
    details = SLIDE_DETAILS[topic_for_slot()][number-1]
    for index, fact in enumerate(details):
        label = "• " + fact
        if d.textbbox((0,0),label,font=font(25))[2] > W-118:
            raise RuntimeError("EDITORIAL_SLIDE_DETAIL_OVERFLOW")
        d.text((62,1159+index*36),label,font=font(25),fill=(218,220,221))
    d.line((60,1240,1020,1240),fill=(71,76,79),width=2)
    d.text((60,1252),"INFINEX  ·  IDEAS EN HIERRO",font=font(25,True),fill=ORANGE)
    d.text((60,1300),"Fotografía ilustrativa · Pexels",font=font(18),fill=GRAY)
    canvas.save(out,"JPEG",quality=92,subsampling=0,optimize=True)

def build():
    if not LOGO.exists(): raise RuntimeError("LOGO_NOT_FOUND")
    pool=photo_candidates(topic_for_slot())
    if len(pool)<3:
        raise RuntimeError("EDITORIAL_AUTOREPAIR_NO_THREE_FRESH_STOCK_PHOTOS")
    _,_,previous_sha,previous_looks=used_photos(BASE,exclude=MEDIA_DIR/"sources.json")
    chosen=[]
    rendered_sha=[]
    rendered_looks=[]
    MEDIA_DIR.mkdir(parents=True,exist_ok=True)
    edition=(DATE-date(2026,11,19)).days*2+(0 if SLOT=="09" else 1)
    titles=EDITORIAL_TITLES or headings_for(topic_for_slot(),edition)
    manifest={"date":DAY_KEY,"slot":SLOT,"destination":IG_USERNAME,"license":"https://www.pexels.com/license/",
              "not_actual_infinex_works":True,"titles":list(titles),
              "sources":[],"images":[]}
    for category,photo in pool:
        if len(chosen)>=3:break
        next_number=len(chosen)+1
        out=MEDIA_DIR/f"{next_number:02}.jpg"
        try:
            image=download_photo(photo)
            render_slide(image,category,next_number,out)
            if out.stat().st_size<50000:raise RuntimeError("JPG_TOO_SMALL")
            sha=hashlib.sha256(out.read_bytes()).hexdigest()
            visual=file_image_signature(out)
            if sha in previous_sha or sha in rendered_sha or any(
                hamming(visual,old)<=3 for old in [*previous_looks,*rendered_looks]):
                raise RuntimeError("EDITORIAL_AUTOREPAIR_SIMILAR_OR_REUSED_VISUAL")
            chosen.append((category,photo))
            rendered_sha.append(sha)
            rendered_looks.append(visual)
            manifest["sources"].append({
                "id":photo["id"],"category":category,
                "page":photo["page"],"author":photo.get("author","Pexels")})
            manifest["images"].append({
                "path":str(out.relative_to(BASE)).replace("\\","/"),"sha256":sha})
        except (RuntimeError,ValueError,OSError) as exc:
            log("EDITORIAL_REPLACE_IMAGE_WITH_NEXT_CANDIDATE",
                str(photo.get("id","?")),str(exc)[:100])
            continue
    if len(chosen)!=3:
        raise RuntimeError("EDITORIAL_AUTOREPAIR_CANDIDATES_EXHAUSTED_"+topic_for_slot().upper())
    (MEDIA_DIR/"sources.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return chosen,manifest

def review_before_publish(chosen,manifest,caption):
    """Automated preflight: correct brand, approved text, unique licensed photos and dimensions."""
    expected_group={"puertas":"gates","escaleras":"structures",
                    "cerramientos":"gates","soldadura":"welding"}[topic_for_slot()]
    if len(chosen)!=3 or {g for g,p in chosen}!={expected_group}:
        raise RuntimeError("CONTENT_MIXED_THEMES_NOT_ALLOWED")
    if len({str(p["id"]) for g,p in chosen})!=3:
        raise RuntimeError("CONTENT_REPEATED_PHOTO")
    validate_headings(manifest.get("titles"))
    edition=(DATE-date(2026,11,19)).days*2+(0 if SLOT=="09" else 1)
    if manifest.get("titles")!=list(EDITORIAL_TITLES or headings_for(topic_for_slot(),edition)):
        raise RuntimeError("EDITORIAL_TITLES_DO_NOT_MATCH_RENDERED_SLIDES")
    ensure_unique(BASE,manifest,exclude=MEDIA_DIR/"sources.json")
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

def check_latest_topic():
    # Compare with the real latest visible publication, including manual and
    # one-off campaigns. If the subject is ambiguous, do not publish.
    response = api(IG_ID+"/media?fields=id,caption,media_type,timestamp&limit=10")
    preceding = assert_not_consecutive(response.get("data"), topic_for_slot())
    log("EDITORIAL_NO_CONSECUTIVE_TOPIC_PASSED", preceding or "first_post",
        "next", topic_for_slot())


def previous_instagram_topic():
    recent=api(IG_ID+"/media?fields=id,caption,media_type,timestamp&limit=10").get("data")
    if not isinstance(recent,list):
        raise RuntimeError("INFINEX_INSTAGRAM_MEDIA_UNAVAILABLE")
    if not recent:
        return None
    result=topic_from_caption(recent[0].get("caption",""))
    if result is None:
        raise RuntimeError("INFINEX_PREVIOUS_POST_TOPIC_NEEDS_REVIEW")
    return result

def regenerate_until_approved(previous_topic=None):
    """Replace unsuitable photographs, claims, titles or even the subject.

    This routine never disables originality/legal/brand checks. A true lack
    of usable stock or broken Meta access remains a technical error.
    """
    failed=set()
    for _ in range(len(TOPICS)):
        try:
            prepare_editorial_plan(previous_topic,failed)
        except RuntimeError:
            break
        theme=topic_for_slot()
        try:
            chosen,manifest=build()
            caption=caption_for(chosen)
            review_before_publish(chosen,manifest,caption)
            log("EDITORIAL_AUTOREPAIR_FINAL_QA_PASSED",theme,
                "source_photos",len(chosen),"titles",len(manifest["titles"]))
            return chosen,manifest,caption
        except RuntimeError as exc:
            if not str(exc).startswith(("EDITORIAL_","CONTENT_","JPG_","STOCK_")):
                raise
            failed.add(theme)
            log("EDITORIAL_AUTOREPAIR_REGENERATE_NEXT_PROPOSAL",
                theme,str(exc)[:115])
    raise RuntimeError("EDITORIAL_REPLENISH_OR_REVIEW_CANDIDATES_REQUIRED")

def find_published_for_slot():
    date_line="📅 "+DATE.strftime("%d/%m/%Y")+" · "+SLOT_TIME
    for item in api(IG_ID+"/media?fields=id,caption,media_type,permalink&limit=100").get("data",[]):
        if date_line in (item.get("caption") or "") and item.get("media_type")=="CAROUSEL_ALBUM":
            return item
    return None

def dry_run():
    if DATE>=START_DATE and not is_scheduled(DATE,SLOT,'carousel'):
        log('INFINEX_CAROUSEL_NOT_SCHEDULED',DAY_KEY,SLOT)
        return
    preflight()
    chosen,manifest,caption=regenerate_until_approved(previous_instagram_topic())
    log("DRY_RUN_OK","date",DAY_KEY,"slot",SLOT,"images",len(manifest["images"]))
    log("SAFETY","NO_POST","NO_COMMIT","TOKEN_NOT_PRINTED")
    for source in manifest["sources"]:log("LICENSED_SOURCE",source["page"])

def publish():
    # Definitive policy: twelve carousels and two Reels, two slots every day.
    if DATE>=START_DATE and not is_scheduled(DATE,SLOT,"carousel"):
        log("INFINEX_CAROUSEL_NOT_SCHEDULED",DAY_KEY,SLOT)
        return
    if DATE>=START_DATE and datetime.now(TZ)<datetime.combine(DATE,dtime(int(SLOT)),tzinfo=TZ):
        log("INFINEX_CAROUSEL_NOT_YET_DUE",DAY_KEY,SLOT)
        return
    preflight()
    # Do not require new stock to verify/reconcile an already-published slot.
    previous=(json.loads(RECORD_FILE.read_text(encoding="utf-8"))
              if RECORD_FILE.exists() else None)
    if previous and (previous.get("do_not_republish") or
                     previous.get("status")=="REJECTED_BY_USER"):
        log("SKIPPED_USER_REJECTED",DAY_KEY,SLOT)
        return
    if previous and previous.get("status")=="PUBLISHED_VERIFIED":
        log("SKIPPED_ALREADY_VERIFIED",DAY_KEY,SLOT,previous.get("permalink",""))
        return
    # Check for an actual posted slot before generating other images/copy.
    # This protects against replay after a lost local ledger or crash.
    if not previous:
        existing=find_published_for_slot()
        if existing:
            published_caption=existing.get("caption","")
            post=verify_post(existing["id"],published_caption)
            state={"date":DAY_KEY,"slot":SLOT,"target":IG_USERNAME,
                   "account_id":IG_ID,"caption":published_caption,
                   "status":"PUBLISHED_VERIFIED","media_id":str(post["id"]),
                   "permalink":post["permalink"],"timestamp":post.get("timestamp")}
            atomic_record(state)
            commit([str(RECORD_FILE.relative_to(BASE))],
                   "INFINEX reconciled existing slot "+DAY_KEY+" "+SLOT)
            log("RECONCILED_EXISTING_SLOT",post["permalink"])
            return
        chosen,manifest,expected_caption=regenerate_until_approved(previous_instagram_topic())
    else:
        expected_caption=previous.get("caption") or caption_for([])
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
    check_latest_topic()
    if previous:
        if (previous.get("publish_attempt_started") or previous.get("media_id") or
            previous.get("status") in ("PUBLISHING_RESULT_UNCERTAIN_NO_RETRY",
                                       "PUBLISH_SENT_NOT_VERIFIED")):
            # An uncertain media_publish must NEVER be resent blindly.
            log("BLOCKED_UNCERTAIN_POST_NO_DUPLICATE",DAY_KEY,SLOT)
            raise RuntimeError("UNCONFIRMED_META_PUBLISH_NO_AUTOMATIC_RETRY")
        log("RESUMING_SAFE_PRE_PUBLISH_FAILURE",DAY_KEY,SLOT)
    if previous:
        chosen,manifest=build()
        review_before_publish(chosen,manifest,expected_caption)
    # Reserve each source and every headline permanently before any Meta upload.
    reserved=reserve(BASE,manifest,DAY_KEY,SLOT,MEDIA_DIR/"sources.json")
    state={"date":DAY_KEY,"slot":SLOT,"target":IG_USERNAME,"account_id":IG_ID,
           "status":"CLAIMED_NO_RETRY","caption":expected_caption,
           "images":manifest["images"],"media_id":None,"children":[],"creation_id":None,
           "publish_attempt_started":False,
           "attempt_count":(previous or {}).get("attempt_count",0)+1,
           "source":"Pexels; illustrative photos, not INFINEX jobs"}
    atomic_record(state)
    commit([str(RECORD_FILE.relative_to(BASE)),str(MEDIA_DIR.relative_to(BASE)),REGISTRY],
           "INFINEX reserve unique photos and headlines "+DAY_KEY+" "+SLOT)
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
        # Comprobar de nuevo justo antes de la unica publicacion publica.
        check_latest_topic()
        confirmed_reserved(BASE,DAY_KEY,SLOT,manifest)
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
            if day>=START_DATE and not is_scheduled(day,slot,"carousel"):
                log("RECOVERY_NON_CAROUSEL_SLOT_SKIPPED",day.isoformat(),slot)
                continue
            if slot=="09" and day==date(2026,11,20):
                log("RECOVERY_HISTORICAL_MORNING_ALREADY_HANDLED",day.isoformat())
                continue
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
            if state and (state.get("do_not_republish") or
                          state.get("status")=="REJECTED_BY_USER"):
                log("RECOVERY_SKIPPED_USER_REJECTED",day.isoformat(),slot)
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
