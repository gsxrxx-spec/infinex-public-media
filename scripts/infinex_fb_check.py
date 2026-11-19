#!/usr/bin/env python3
"""INFINEX Facebook page-token preflight, strictly read-only. Never print secrets."""
import json
import os
import sys
import urllib.error
import urllib.request

GRAPH = "https://graph.facebook.com/v27.0/"
EXPECTED_PAGE = "1598994686632912"


def fetch(endpoint, token):
    req = urllib.request.Request(
        GRAPH + endpoint,
        headers={"Authorization": "Bearer " + token,
                 "User-Agent": "INFINEX-Page-Preflight/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        raise RuntimeError("META_HTTP_" + str(err.code)) from None
    except Exception:
        raise RuntimeError("META_NETWORK_FAILURE") from None


def main():
    token = os.environ.get("INFINEX_FB_PAGE_TOKEN", "").strip()
    if len(token) < 50:
        raise RuntimeError("FACEBOOK_SECRET_NOT_CONFIGURED")
    identity = fetch("me?fields=id,name", token)
    if str(identity.get("id")) != EXPECTED_PAGE:
        print("TOKEN_IS_USER_NOT_PAGE")
        permissions = fetch("me/permissions", token)
        grants = {item.get("permission"): item.get("status")
                  for item in permissions.get("data", [])}
        for requested in ("pages_show_list", "pages_read_engagement", "pages_manage_posts"):
            print("TOKEN_PERMISSION_" + requested.upper(),
                  grants.get(requested, "NOT_GRANTED_OR_MISSING"))
        accounts = fetch("me/accounts?fields=id,name,tasks,access_token&limit=50", token)
        candidates = [p for p in accounts.get("data", [])
                      if str(p.get("id")) == EXPECTED_PAGE]
        print("TARGET_PAGE_VISIBLE_TO_USER_TOKEN", bool(candidates))
        print("TARGET_PAGE_TOKEN_AVAILABLE_IN_META",
              bool(candidates and len(candidates[0].get("access_token", "")) > 50))
        raise RuntimeError("REPLACE_GITHUB_SECRET_WITH_TARGET_PAGE_TOKEN")
    print("FACEBOOK_PAGE_IDENTITY_OK")
    page = fetch(EXPECTED_PAGE + "?fields=id,name", token)
    if str(page.get("id")) != EXPECTED_PAGE:
        raise RuntimeError("FACEBOOK_PAGE_IDENTITY_MISMATCH")
    print("FACEBOOK_PAGE_READ_OK")
    feed = fetch(EXPECTED_PAGE + "/feed?fields=id,message,permalink_url&limit=1", token)
    if not isinstance(feed.get("data"), list):
        raise RuntimeError("FACEBOOK_FEED_READ_FAILED")
    print("FACEBOOK_FEED_READ_OK")
    print("FACEBOOK_CHECK_PASSED_NO_PUBLICATION")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("INFINEX_FACEBOOK_CHECK_ERROR", str(exc)[:90])
        sys.exit(1)
