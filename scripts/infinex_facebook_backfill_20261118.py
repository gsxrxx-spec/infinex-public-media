#!/usr/bin/env python3
"""INFINEX: mirror the exact verified 2026-11-18 IG carousel once to Facebook.

Intentionally one-off, source-locked and fail-closed; never discloses credentials.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageStat
import infinex_facebook as fb

IG_ID = "17841435427297631"
IG_POST_ID = "18052793363820744"
IG_PERMALINK = "https://www.instagram.com/p/Df5J_XcFjaF/"
IG_CAPTION_SHA = "a337bfc4ebd02e1a44c7765d10c618e0ad38d71a4d11079883cd89116b1f2e1f"
CHILD_IDS = ["18119595661825289", "18650182951044606", "18150582004586479"]
DATE = "2026-11-18"
IMAGE_ROOT = "assets/2026-11-18/visual-b/"
RECORD = fb.BASE / "records" / ("2026-11-18_fb_ig_" + IG_POST_ID + ".json")

def ig_api(path):
    token = os.getenv("INFINEX_IG_TOKEN", "").strip()
    if len(token) < 50:
        raise RuntimeError("INSTAGRAM_SECRET_MISSING")
    req = urllib.request.Request(
        fb.GRAPH + path,
        headers={"Authorization": "Bearer " + token,
                 "User-Agent": "INFINEX-Exact-Carousel-Crosspost/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as result:
            return json.load(result)
    except urllib.error.HTTPError as err:
        raise RuntimeError("INSTAGRAM_READ_HTTP_" + str(err.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("INSTAGRAM_READ_NETWORK_FAILURE") from None

def verify_exact_source():
    account = ig_api(IG_ID + "?fields=id,username")
    if str(account.get("id")) != IG_ID or account.get("username") != "infinex_2025":
        raise RuntimeError("INSTAGRAM_ACCOUNT_CHANGED")
    item = ig_api(IG_POST_ID +
        "?fields=id,media_type,timestamp,permalink,caption,children{id,media_type,media_url}")
    if (str(item.get("id")) != IG_POST_ID or
        item.get("media_type") != "CAROUSEL_ALBUM" or
        item.get("permalink") != IG_PERMALINK or
        not item.get("timestamp", "").startswith(DATE)):
        raise RuntimeError("WRONG_INSTAGRAM_POST")
    caption = item.get("caption", "")
    if (hashlib.sha256(caption.encode("utf-8")).hexdigest() != IG_CAPTION_SHA or
        "INFINEX" not in caption):
        raise RuntimeError("INSTAGRAM_CAPTION_NOT_IDENTICAL")
    children = item.get("children", {}).get("data", [])
    if [str(c.get("id")) for c in children] != CHILD_IDS or any(
            c.get("media_type") != "IMAGE" for c in children):
        raise RuntimeError("INSTAGRAM_CAROUSEL_PHOTOS_CHANGED")
    for index, child in enumerate(children, 1):
        src = child.get("media_url", "")
        if not src.startswith("https://"):
            raise RuntimeError("SOURCE_IMAGE_NOT_AVAILABLE")
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                ig_image = Image.open(BytesIO(r.read())).convert("RGB").resize((100,120))
        except Exception:
            raise RuntimeError("SOURCE_IMAGE_READ_FAILED") from None
        local = fb.BASE / IMAGE_ROOT / ("infinex_visual_" + str(index) + ".jpg")
        if not local.is_file():
            raise RuntimeError("LOCAL_APPROVED_IMAGE_MISSING")
        original = Image.open(local).convert("RGB").resize((100,120))
        diff = ImageStat.Stat(ImageChops.difference(ig_image, original)).mean
        similarity = 1 - sum(diff)/(3*255)
        if similarity < .99:
            raise RuntimeError("SOURCE_PHOTO_NOT_IDENTICAL_" + str(index))
    print("IG_SOURCE_VERIFIED", IG_POST_ID, "PHOTOS", len(children),
          "CAPTION_SHA", IG_CAPTION_SHA)
    return caption

def public_images():
    entries = []
    for index in (1, 2, 3):
        p = fb.BASE / IMAGE_ROOT / ("infinex_visual_" + str(index) + ".jpg")
        relative = p.relative_to(fb.BASE).as_posix()
        local = hashlib.sha256(p.read_bytes()).hexdigest()
        url = fb.RAW + relative
        req = urllib.request.Request(url, headers={"User-Agent":"INFINEX-Asset-Check"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
                kind = r.headers.get("Content-Type", "")
        except Exception:
            raise RuntimeError("PUBLIC_IMAGE_NOT_ACCESSIBLE_" + str(index)) from None
        if local != hashlib.sha256(data).hexdigest() or "image/" not in kind:
            raise RuntimeError("PUBLIC_IMAGE_NOT_IDENTICAL_" + str(index))
        entries.append({"url": url, "sha256": local, "file": relative})
    return entries

def store(state, reason):
    fb.save(RECORD, state)
    fb.commit(RECORD, "INFINEX FB historical mirror " + reason)

def existing(caption):
    return fb.existing_post(caption)

def run():
    # 1. Source and destination validation, all before publishing.
    caption = verify_exact_source()
    fb.page_preflight()
    state = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    posted = existing(caption)
    if posted:
        state.update({"status": "PUBLISHED_VERIFIED",
                      "source_ig_id": IG_POST_ID,
                      "source_ig_permalink": IG_PERMALINK,
                      "caption_sha256": IG_CAPTION_SHA,
                      "page_id": fb.PAGE_ID,
                      "post_id": str(posted["id"]),
                      "permalink": posted.get("permalink_url", ""),
                      "verified_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat()})
        store(state, "reconcile 2026-11-18")
        print("FACEBOOK_ALREADY_EXISTS_VERIFIED", posted["id"])
        return
    if state.get("status") == "PUBLISHED_VERIFIED":
        print("FACEBOOK_PREVIOUSLY_VERIFIED_NO_REPOST")
        return
    if state.get("publish_attempt_started"):
        raise RuntimeError("UNCERTAIN_PRIOR_PUBLICATION_NO_RETRY")
    assets = public_images()
    state.update({"source_ig_id": IG_POST_ID,
                  "source_ig_permalink": IG_PERMALINK,
                  "caption_sha256": IG_CAPTION_SHA,
                  "date": DATE, "page_id": fb.PAGE_ID,
                  "status": "PREPARED_NO_PUBLIC_POST",
                  "publish_attempt_started": False,
                  "assets": [{k: a[k] for k in ("file", "sha256")} for a in assets]})
    store(state, "prepare 2026-11-18")
    try:
        uploaded = list(state.get("photo_ids", []))
        if len(uploaded) > 3:
            raise RuntimeError("WRONG_UPLOAD_LEDGER")
        for asset in assets[len(uploaded):]:
            item = fb.api(fb.PAGE_ID + "/photos",
                          {"url": asset["url"], "published": "false"})
            photo_id = str(item.get("id", ""))
            if not photo_id.isdigit():
                raise RuntimeError("FB_UPLOADED_PHOTO_ID_MISSING")
            uploaded.append(photo_id)
            state["photo_ids"] = uploaded
            fb.save(RECORD, state)
        if len(uploaded) != 3:
            raise RuntimeError("WRONG_PHOTO_COUNT")
        fields = {"message": caption}
        for index, item_id in enumerate(uploaded):
            fields["attached_media[" + str(index) + "]"] = json.dumps(
                {"media_fbid": item_id})
        # Reserve a single public post attempt in remote Git ledger first.
        state["status"] = "PUBLIC_POST_RESULT_UNCERTAIN"
        state["publish_attempt_started"] = True
        store(state, "reserve one send 2026-11-18")
        try:
            result = fb.api(fb.PAGE_ID + "/feed", fields)
        except RuntimeError as error:
            # Only a definite Meta permissions denial can be safely marked rejected.
            state["last_error"] = str(error)[:80]
            if str(error).startswith("FB_HTTP_400_CODE_10_"):
                state["status"] = "META_REJECTED_PERMISSION_NO_POST"
                state["publish_attempt_started"] = False
            store(state, "send error 2026-11-18")
            raise
        if not result.get("id"):
            raise RuntimeError("FACEBOOK_POST_ID_NOT_RETURNED")
        state["post_id"] = str(result["id"])
        state["status"] = "POST_SENT_VERIFYING"
        fb.save(RECORD, state)
        for attempt in range(6):
            found = existing(caption)
            if found:
                if str(found.get("id")) != state["post_id"]:
                    raise RuntimeError("FACEBOOK_READBACK_ID_MISMATCH")
                state["status"] = "PUBLISHED_VERIFIED"
                state["permalink"] = found.get("permalink_url", "")
                state["verified_at"] = datetime.now(ZoneInfo("Europe/Madrid")).isoformat()
                store(state, "verified 2026-11-18")
                print("FACEBOOK_POST_PUBLISHED_VERIFIED",
                      state["post_id"], state["permalink"])
                return
            time.sleep(5)
        store(state, "readback pending 2026-11-18")
        raise RuntimeError("PUBLISHED_BUT_READBACK_PENDING_NO_REPOST")
    except Exception as error:
        # Never auto-retry an uncertain public post.
        state["error_type"] = str(error)[:90]
        fb.save(RECORD, state)
        try:
            store(state, "failed 2026-11-18")
        except Exception:
            pass
        raise

if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("INFINEX_HISTORICAL_FB_ERROR", str(exc)[:120])
        sys.exit(1)
