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
        raise RuntimeError("TOKEN_IS_NOT_EXPECTED_PAGE_TOKEN")
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
