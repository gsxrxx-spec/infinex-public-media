"""INFINEX Facebook mirror: isolated, offline duplicate-safety checks."""
import importlib.util
import tempfile
import json
import hashlib
import unittest
from datetime import date, timezone
from pathlib import Path
import zoneinfo

f = Path(__file__).resolve().parents[1] / "scripts" / "infinex_facebook.py"
sp = importlib.util.spec_from_file_location("mirror_fb_tests", f)
m = importlib.util.module_from_spec(sp)
_original_zoneinfo = zoneinfo.ZoneInfo
try:
    zoneinfo.ZoneInfo = lambda _: timezone.utc  # Only for isolated Windows tests
    sp.loader.exec_module(m)
finally:
    zoneinfo.ZoneInfo = _original_zoneinfo
day = date(2026, 11, 19)
caption = "INFINEX #INFINEX\nNo son obras ejecutadas por INFINEX.\n19/11/2026 · 09:00"

class Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.orig = (m.BASE, m.api, m.commit, m.public_assets_verified)
        self.addCleanup(self.restore)
        m.BASE = Path(self.t.name)
        m.commit = lambda path, label: None
        m.public_assets_verified = lambda imgs: None
        self.ig, self.fb, manifest = m.ledger_paths(day, "09")
        manifest.parent.mkdir(parents=True)
        self.ig.parent.mkdir(parents=True)
        images = []
        for i in range(3):
            p = manifest.parent / ("%02d.jpg" % (i+1))
            p.write_bytes(bytes([i+1]) * 60000)
            images.append({"path": p.relative_to(m.BASE).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        self.ig.write_text(json.dumps({"status": "PUBLISHED_VERIFIED", "media_id": "123456789",
                         "permalink": "https://www.instagram.com/p/example/", "caption": caption, "images": images}), encoding="utf-8")
        manifest.write_text(json.dumps({"date": day.isoformat(), "slot": "09", "destination": "infinex_2025",
                            "license": "https://www.pexels.com/license/", "not_actual_infinex_works": True,
                            "sources": [{}, {}, {}], "images": images}), encoding="utf-8")

    def restore(self):
        m.BASE, m.api, m.commit, m.public_assets_verified = self.orig

    def test_existing_post_no_republish(self):
        def api(endpoint, fields=None):
            self.assertIsNone(fields)
            return {"data": [{"id": "1598994686632912_123", "message": caption}]}
        m.api = api
        self.assertTrue(m.mirror(day, "09"))
        self.assertEqual(json.loads(self.fb.read_text())["status"], "PUBLISHED_VERIFIED")

    def test_single_post_and_readback(self):
        post_count = [0]
        def api(endpoint, fields=None):
            if fields is None:
                return {"data": ([{"id": "1598994686632912_456", "message": caption}] if post_count[0] else [])}
            if endpoint.endswith("/photos"):
                return {"id": "999123"}
            if endpoint.endswith("/feed"):
                self.assertEqual(fields["message"], caption)
                post_count[0] += 1
                return {"id": "1598994686632912_456"}
            raise AssertionError(endpoint)
        m.api = api
        self.assertTrue(m.mirror(day, "09"))
        self.assertTrue(m.mirror(day, "09"))
        self.assertEqual(post_count[0], 1)

    def test_network_uncertainty_blocks_retry(self):
        posts = [0]
        def api(endpoint, fields=None):
            if fields is None:
                return {"data": []}
            if endpoint.endswith("/photos"):
                return {"id": "999123"}
            posts[0] += 1
            raise RuntimeError("FB_NETWORK_FAILURE")
        m.api = api
        with self.assertRaisesRegex(RuntimeError, "FB_NETWORK_FAILURE"):
            m.mirror(day, "09")
        with self.assertRaisesRegex(RuntimeError, "FACEBOOK_UNCERTAIN_NO_AUTOMATIC_REPOST"):
            m.mirror(day, "09")
        self.assertEqual(posts[0], 1)

    def test_permission_denial_can_retry(self):
        post_attempts = [0]
        def api(endpoint, fields=None):
            if fields is None:
                return {"data": []}
            if endpoint.endswith("/photos"):
                return {"id": "999123"}
            post_attempts[0] += 1
            raise RuntimeError("FB_HTTP_400_CODE_10_SUBCODE_none")
        m.api = api
        for i in range(2):
            with self.assertRaisesRegex(RuntimeError, "FB_HTTP_400_CODE_10"):
                m.mirror(day, "09")
        self.assertEqual(post_attempts[0], 2)
        self.assertFalse(json.loads(self.fb.read_text())["publish_attempt_started"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
