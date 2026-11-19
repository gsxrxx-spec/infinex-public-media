#!/usr/bin/env python3
"""INFINEX Facebook mirror: exact IG assets/caption, idempotent and audited."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
PAGE_ID = "1598994686632912"
GRAPH = "https://graph.facebook.com/v27.0/"
RAW = "https://raw.githubusercontent.com/gsxrxx-spec/infinex-public-media/main/"
TZ = ZoneInfo("Europe/Madrid")
START = date(2026, 11, 19)

def info(*items):
    print(*items, flush=True)

def access_token():
    token = os.environ.get("INFINEX_FB_PAGE_TOKEN", "").strip()
    if len(token) < 50:
        raise RuntimeError("FACEBOOK_PAGE_TOKEN_NOT_CONFIGURED")
    return token

def api(endpoint, fields=None):
    body = urllib.parse.urlencode(fields).encode("utf-8") if fields is not None else None
    req = urllib.request.Request(
        GRAPH + endpoint, data=body, method="POST" if body is not None else "GET",
        headers={"Authorization": "Bearer " + access_token(),
                 "User-Agent": "INFINEX-Verified-IG-Mirror/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        try:
            detail = json.loads(err.read(4096)).get("error", {})
            code = str(detail.get("code", "unknown"))
            subcode = str(detail.get("error_subcode", "none"))
        except Exception:
            code, subcode = "unavailable", "unavailable"
        raise RuntimeError("FB_HTTP_" + str(err.code) + "_CODE_" + code + "_SUBCODE_" + subcode) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("FB_NETWORK_FAILURE") from None

def page_preflight():
    identity = api("me?fields=id,name")
    if str(identity.get("id")) != PAGE_ID:
        raise RuntimeError("FACEBOOK_TARGET_PAGE_MISMATCH")
    page = api(PAGE_ID + "?fields=id,name")
    if str(page.get("id")) != PAGE_ID:
        raise RuntimeError("FACEBOOK_PAGE_ID_READ_MISMATCH")
    # /feed GET fails with Meta error 10 on this app. /published_posts is verified.
    recent = api(PAGE_ID + "/published_posts?fields=id,message,permalink_url&limit=1")
    if not isinstance(recent.get("data"), list):
        raise RuntimeError("FACEBOOK_PUBLISHED_POSTS_READ_UNAVAILABLE")
    info("FACEBOOK_PAGE_PREFLIGHT_PASSED", PAGE_ID)

def existing_post(caption):
    after = None
    for _ in range(4):
        path = PAGE_ID + "/published_posts?fields=id,message,permalink_url&limit=100"
        if after:
            path += "&after=" + urllib.parse.quote(after, safe="")
        data = api(path)
        items = data.get("data")
        if not isinstance(items, list):
            raise RuntimeError("FACEBOOK_POST_LIST_INVALID")
        for item in items:
            if item.get("message") == caption:
                if not item.get("id"):
                    raise RuntimeError("FACEBOOK_MATCH_WITHOUT_ID")
                return item
        if not items:
            return None
        cursor = data.get("paging", {}).get("cursors", {}).get("after")
        if not cursor or cursor == after or not data.get("paging", {}).get("next"):
            return None
        after = cursor
    raise RuntimeError("FACEBOOK_PAGINATION_EXHAUSTED_NO_SAFE_REPOST")

def ledger_paths(day, slot):
    tag = day.isoformat() + "_" + slot
    return (BASE / "records" / (tag + ".json"),
            BASE / "records" / (tag + "_fb.json"),
            BASE / "assets" / "daily" / day.isoformat() / slot / "sources.json")

def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)

def commit(path, label):
    subprocess.run(["git", "config", "user.name", "INFINEX Scheduler"],
                   cwd=BASE, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email",
                    "infinex-automation@users.noreply.github.com"],
                   cwd=BASE, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "add", "--", str(path.relative_to(BASE))],
                   cwd=BASE, check=True, stdout=subprocess.DEVNULL)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=BASE).returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", label], cwd=BASE,
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE,
                   check=True, stdout=subprocess.DEVNULL)

def verified_ig(day, slot):
    ig_file, fb_file, manifest_file = ledger_paths(day, slot)
    if not ig_file.exists():
        return None
    ig = json.loads(ig_file.read_text(encoding="utf-8"))
    if ig.get("status") != "PUBLISHED_VERIFIED":
        return None
    if (not str(ig.get("media_id", "")).isdigit() or
        not str(ig.get("permalink", "")).startswith("https://www.instagram.com/")):
        raise RuntimeError("IG_VERIFIED_RECORD_INVALID")
    caption = ig.get("caption", "")
    if ("#INFINEX" not in caption or
        "No son obras ejecutadas por INFINEX." not in caption or
        day.strftime("%d/%m/%Y") not in caption or
        (" · " + slot + ":00") not in caption):
        raise RuntimeError("IG_ORIGINAL_CAPTION_UNAPPROVED")
    if not manifest_file.exists():
        raise RuntimeError("IG_ORIGINAL_ASSETS_MISSING")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    images = manifest.get("images", [])
    if (manifest.get("date") != day.isoformat() or
        manifest.get("slot") != slot or
        manifest.get("destination") != "infinex_2025" or
        manifest.get("license") != "https://www.pexels.com/license/" or
        manifest.get("not_actual_infinex_works") is not True or
        len(images) != 3 or len(manifest.get("sources", [])) != 3 or
        ig.get("images") != images):
        raise RuntimeError("IG_SOURCE_MANIFEST_MISMATCH")
    paths = set()
    for image in images:
        relative = Path(image.get("path", ""))
        if (relative.is_absolute() or ".." in relative.parts or
            not relative.as_posix().startswith("assets/daily/")):
            raise RuntimeError("FB_UNSAFE_MEDIA_PATH")
        if relative.as_posix() in paths:
            raise RuntimeError("FB_DUPLICATE_MEDIA_ASSET")
        paths.add(relative.as_posix())
        file = BASE / relative
        if (not file.is_file() or file.stat().st_size < 50000 or
            hashlib.sha256(file.read_bytes()).hexdigest() != image.get("sha256")):
            raise RuntimeError("IG_IMAGE_HASH_MISMATCH")
    return ig, images, caption, fb_file

def public_assets_verified(images):
    for image in images:
        url = RAW + image["path"]
        req = urllib.request.Request(url, headers={"User-Agent": "INFINEX-Asset-Check"})
        try:
            with urllib.request.urlopen(req, timeout=24) as result:
                data = result.read()
                kind = result.headers.get("Content-Type", "")
            if "image/" not in kind or hashlib.sha256(data).hexdigest() != image["sha256"]:
                raise RuntimeError("FB_PUBLIC_ASSET_HASH_MISMATCH")
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("FB_PUBLIC_ASSET_NOT_AVAILABLE") from None

def reconcile(state, fb_file, caption, day, slot):
    posted = existing_post(caption)
    if posted is None:
        return False
    if state.get("post_id") and str(state["post_id"]) != str(posted["id"]):
        raise RuntimeError("FACEBOOK_SAME_CAPTION_MULTIPLE_IDS")
    state.update({"date": day.isoformat(), "slot": slot, "page_id": PAGE_ID,
                  "caption": caption, "status": "PUBLISHED_VERIFIED",
                  "post_id": str(posted["id"]),
                  "permalink": posted.get("permalink_url", ""),
                  "verified_at": datetime.now(TZ).isoformat()})
    save(fb_file, state)
    commit(fb_file, "INFINEX verified FB " + day.isoformat() + " " + slot)
    info("FACEBOOK_VERIFIED", day.isoformat(), slot, state["post_id"])
    return True

def mirror(day, slot):
    material = verified_ig(day, slot)
    if material is None:
        return False
    ig, images, caption, fb_file = material
    state = json.loads(fb_file.read_text(encoding="utf-8")) if fb_file.exists() else {}
    if state.get("status") == "PUBLISHED_VERIFIED":
        return True
    # Check Meta before any publishing action, even if local ledger was lost.
    if reconcile(state, fb_file, caption, day, slot):
        return True
    if (state.get("publish_attempt_started") or state.get("post_id") or
        state.get("status") in ("PUBLISHING_RESULT_UNCERTAIN_NO_RETRY",
                                "POST_SENT_NOT_VERIFIED")):
        raise RuntimeError("FACEBOOK_UNCERTAIN_NO_AUTOMATIC_REPOST")
    public_assets_verified(images)
    state.update({"date": day.isoformat(), "slot": slot, "page_id": PAGE_ID,
                  "source_ig_media_id": str(ig["media_id"]),
                  "source_ig_permalink": ig["permalink"],
                  "caption": caption, "images": images,
                  "status": "PRE_PUBLISH_PREPARED",
                  "publish_attempt_started": False,
                  "attempt_count": int(state.get("attempt_count", 0)) + 1})
    save(fb_file, state)
    commit(fb_file, "INFINEX prepare FB mirror " + day.isoformat() + " " + slot)
    try:
        photo_ids = []
        for image in images:
            res = api(PAGE_ID + "/photos",
                      {"url": RAW + image["path"], "published": "false"})
            media_id = str(res.get("id", ""))
            if not media_id.isdigit():
                raise RuntimeError("FB_PHOTO_UPLOAD_ID_MISSING")
            photo_ids.append(media_id)
            state["uploaded_photo_ids"] = photo_ids
            save(fb_file, state)
        post_fields = {"message": caption}
        for index, media_id in enumerate(photo_ids):
            post_fields["attached_media[" + str(index) + "]"] = json.dumps(
                {"media_fbid": media_id})
        # Commit uncertain state BEFORE the sole public-feed POST.
        state["status"] = "PUBLISHING_RESULT_UNCERTAIN_NO_RETRY"
        state["publish_attempt_started"] = True
        save(fb_file, state)
        commit(fb_file, "INFINEX FB single post reserved " + day.isoformat() + " " + slot)
        try:
            result = api(PAGE_ID + "/feed", post_fields)
        except RuntimeError as rejected:
            # Explicit Meta permission denial means the public post was rejected.
            # All other failures remain uncertain, so they cannot auto-repost.
            if str(rejected).startswith("FB_HTTP_400_CODE_10_"):
                state["publish_attempt_started"] = False
                state["status"] = "POST_REJECTED_PERMISSION_SAFE_TO_RETRY"
            raise
        post_id = str(result.get("id", ""))
        if not post_id:
            raise RuntimeError("FB_POST_RESPONSE_ID_MISSING")
        state["post_id"] = post_id
        state["status"] = "POST_SENT_NOT_VERIFIED"
        save(fb_file, state)
        for _ in range(6):
            try:
                if reconcile(state, fb_file, caption, day, slot):
                    return True
            except RuntimeError:
                pass
            time.sleep(4)
        commit(fb_file, "INFINEX FB readback pending " + day.isoformat() + " " + slot)
        raise RuntimeError("FB_POST_SENT_READBACK_PENDING")
    except Exception as error:
        state["last_error_code"] = str(error)[:70]
        if not state.get("publish_attempt_started"):
            state["status"] = "PRE_PUBLISH_FAILED_SAFE_TO_RETRY"
        save(fb_file, state)
        try:
            commit(fb_file, "INFINEX FB state " + day.isoformat() + " " + slot)
        except Exception:
            pass
        raise

def recover():
    page_preflight()
    now = datetime.now(TZ)
    successes, attempts, failures = 0, 0, []
    for days_ago in range(31):
        day = now.date() - timedelta(days=days_ago)
        if day < START:
            break
        for slot in ("09", "17"):
            if datetime.combine(day, dt_time(int(slot), 0), tzinfo=TZ) > now:
                continue
            ig_file, fb_file, _ = ledger_paths(day, slot)
            if not ig_file.is_file():
                continue
            # Older days stay queued; prefer the latest valid posts first.
            if fb_file.is_file():
                try:
                    previous = json.loads(fb_file.read_text(encoding="utf-8"))
                    if previous.get("status") == "PUBLISHED_VERIFIED":
                        continue
                except Exception:
                    failures.append(day.isoformat() + "_" + slot + "_LEDGER_BAD")
                    continue
            if attempts >= 2:
                break
            attempts += 1
            try:
                if mirror(day, slot):
                    successes += 1
            except Exception as error:
                info("FACEBOOK_MIRROR_FAILED", day.isoformat(), slot, str(error)[:90])
                failures.append(day.isoformat() + "_" + slot)
    info("FACEBOOK_RECOVERY_COMPLETED", "attempts", attempts,
         "verified", successes, "failures", len(failures))
    if failures:
        raise RuntimeError("FACEBOOK_RECOVERY_PENDING_" + ",".join(failures[:4]))

def dry_run():
    page_preflight()
    info("FACEBOOK_DRY_RUN_OK", "NO_POST", "NO_COMMIT", "SAME_IG_CONTENT_ONLY")

if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else "dry_run"
        if mode == "dry_run":
            dry_run()
        elif mode in ("recover", "publish"):
            recover()
        elif mode == "verify":
            info("FACEBOOK_VERIFY_NO_POST")
        else:
            raise RuntimeError("UNSUPPORTED_FACEBOOK_MODE")
    except Exception as error:
        info("INFINEX_FB_ERROR", str(error)[:110])
        sys.exit(1)
