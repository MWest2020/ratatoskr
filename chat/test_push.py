# SPDX-License-Identifier: EUPL-1.2
"""Web Push storage: the gate and the bound.

The subscribe route is unprotected behind the device token: any tailnet device
can call it. Whatever goes wrong here therefore grows quietly in a file on the VM.
"""
import importlib
import json
import os
import stat
import tempfile
import unittest


class PushTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["PUSH_SUBS_PATH"] = os.path.join(self.dir, "diep", "subs.json")
        os.environ["PUSH_MAX_SUBS"] = "3"
        import push
        self.push = importlib.reload(push)

    def tearDown(self):
        os.environ.pop("PUSH_SUBS_PATH", None)
        os.environ.pop("PUSH_MAX_SUBS", None)

    def sub(self, ep="https://push.example/abc", p="p" * 10, a="a" * 10):
        return {"endpoint": ep, "keys": {"p256dh": p, "auth": a}}

    # --- gate ---
    def test_a_valid_subscription_is_stored(self):
        self.assertTrue(self.push.add_subscription(self.sub()))
        self.assertEqual(len(self.push.load_subscriptions()), 1)

    def test_only_https_endpoints(self):
        for ep in ("http://push.example/x", "ftp://x", "javascript:x", ""):
            self.assertFalse(self.push.add_subscription(self.sub(ep=ep)), ep)

    def test_the_shape_is_enforced(self):
        for bad in (None, "tekst", [], {}, {"endpoint": "https://x"},
                    {"endpoint": "https://x", "keys": "geen-dict"},
                    {"endpoint": "https://x", "keys": {"p256dh": "p"}}):
            self.assertFalse(self.push.add_subscription(bad), repr(bad))

    def test_overlong_fields_are_refused(self):
        self.assertFalse(self.push.add_subscription(self.sub(ep="https://x/" + "y" * 2000)))
        self.assertFalse(self.push.add_subscription(self.sub(p="p" * 300)))

    def test_extra_fields_are_not_stored(self):
        s = self.sub(); s["stiekem"] = "x" * 100; s["keys"]["extra"] = "y"
        self.assertTrue(self.push.add_subscription(s))
        stored = self.push.load_subscriptions()[0]
        self.assertEqual(set(stored), {"endpoint", "keys"})
        self.assertEqual(set(stored["keys"]), {"p256dh", "auth"})

    # --- bounds and durability ---
    def test_dedup_on_endpoint(self):
        self.push.add_subscription(self.sub(p="eerst"))
        self.push.add_subscription(self.sub(p="tweede"))
        subs = self.push.load_subscriptions()
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["keys"]["p256dh"], "tweede")   # newest wins

    def test_the_cap_drops_the_oldest(self):
        for i in range(5):
            self.push.add_subscription(self.sub(ep=f"https://push.example/{i}"))
        subs = self.push.load_subscriptions()
        self.assertEqual(len(subs), 3)                          # PUSH_MAX_SUBS
        self.assertEqual([s["endpoint"][-1] for s in subs], ["2", "3", "4"])

    def test_the_state_dir_is_created(self):
        # Fresh VM without the mkdir step: this must not throw a
        # FileNotFoundError through do_POST (a traceback without an HTTP answer).
        self.assertTrue(self.push.add_subscription(self.sub()))
        self.assertTrue(os.path.exists(self.push.SUBS_PATH))

    def test_the_file_is_0600(self):
        self.push.add_subscription(self.sub())
        mode = stat.S_IMODE(os.stat(self.push.SUBS_PATH).st_mode)
        self.assertEqual(mode, 0o600, oct(mode))   # per-device push tokens

    def test_a_broken_file_gives_an_empty_list(self):
        os.makedirs(os.path.dirname(self.push.SUBS_PATH), exist_ok=True)
        with open(self.push.SUBS_PATH, "w") as f:
            f.write("{geen json")
        self.assertEqual(self.push.load_subscriptions(), [])
        self.assertTrue(self.push.add_subscription(self.sub()))   # recovers

    def test_json_that_is_not_a_list_gives_an_empty_list(self):
        os.makedirs(os.path.dirname(self.push.SUBS_PATH), exist_ok=True)
        with open(self.push.SUBS_PATH, "w") as f:
            json.dump({"niet": "een lijst"}, f)
        self.assertEqual(self.push.load_subscriptions(), [])


if __name__ == "__main__":
    unittest.main()
