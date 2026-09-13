# SPDX-License-Identifier: EUPL-1.2
"""Does a push actually LEAVE here, correctly encrypted and signed?

Everything about Web Push that can be wrong on our side happens before the
message reaches a push service: the VAPID key comes out of SOPS, the payload is
encrypted to the subscriber's public key, a JWT is signed, and the headers that
decide *when* a phone sees it are attached. None of that was ever provable
without a real device, so it was never proven — while "no notifications" was a
recurring complaint whose cause turned out to be somewhere else three times.

This test stands in for the push service: it makes a browser-shaped subscription
(a real P-256 keypair plus an auth secret), receives the POST on localhost, and
decrypts the body. If this passes, the only remaining unknown is the phone.

Skips rather than fails when SOPS or the age key is missing — the offline
`verify.sh` must not depend on a secret.
"""
import base64
import json
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
VAPID_YAML = os.path.join(os.path.dirname(HERE), "secrets", "vapid.yaml")


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _vapid_or_none():
    """The private key, or None when this machine cannot decrypt secrets."""
    key_file = os.path.expanduser("~/.config/sops/age/keys.txt")
    if not (os.path.exists(VAPID_YAML) and os.path.exists(key_file)):
        return None
    env = dict(os.environ, SOPS_AGE_KEY_FILE=key_file)
    r = subprocess.run(["sops", "-d", VAPID_YAML], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return None
    import yaml
    return yaml.safe_load(r.stdout)["vapid"]


class _PushService(BaseHTTPRequestHandler):
    """What Google's or Apple's endpoint does, minus the phone."""
    received = {}

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        _PushService.received = {"body": self.rfile.read(n),
                                 # lowercase: HTTP header names are
                                 # case-insensitive and requests sends them lower
                                 "headers": {k.lower(): v for k, v in self.headers.items()}}
        self.send_response(201)
        self.end_headers()

    def log_message(self, *a):
        pass


class APushLeavesCorrectly(unittest.TestCase):
    def setUp(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import ec   # noqa: F401
            import http_ece                                            # noqa: F401
            import pywebpush                                           # noqa: F401
        except ImportError:
            self.skipTest("pywebpush/cryptography/http-ece niet beschikbaar")
        self.vapid = _vapid_or_none()
        if not self.vapid:
            self.skipTest("geen SOPS of geen age-sleutel — verzendtest overgeslagen")
        self.srv = HTTPServer(("127.0.0.1", 0), _PushService)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def test_the_payload_arrives_decryptable_and_urgent(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from http_ece import decrypt
        from pywebpush import webpush

        # A subscriber, the way a browser makes one.
        priv = ec.generate_private_key(ec.SECP256R1())
        pub = priv.public_key().public_bytes(serialization.Encoding.X962,
                                             serialization.PublicFormat.UncompressedPoint)
        auth = os.urandom(16)
        sub = {"endpoint": f"http://127.0.0.1:{self.port}/fake/abc",
               "keys": {"p256dh": _b64(pub), "auth": _b64(auth)}}

        payload = json.dumps({"title": "Ratatoskr", "body": "verzendtest", "url": "/"})
        r = webpush(subscription_info=sub, data=payload,
                    vapid_private_key=self.vapid["private"],
                    vapid_claims={"sub": self.vapid.get("subject", "mailto:boomhuis@localhost")},
                    ttl=3600, headers={"Urgency": "high"})
        self.assertEqual(r.status_code, 201)

        got = _PushService.received
        h = got["headers"]
        # Urgency decides WHEN a phone sees it. Without it a push service treats
        # the message as "normal" and may hold it until the device leaves doze —
        # observed 2026-09-08, two pushes arriving late and at the same time. For
        # a chat message, too late is the same as never.
        self.assertEqual(h.get("urgency"), "high")
        self.assertEqual(h.get("ttl"), "3600")
        self.assertEqual(h.get("content-encoding"), "aes128gcm")
        self.assertTrue((h.get("authorization") or "").startswith("vapid t="), h.get("authorization"))

        plain = decrypt(got["body"], private_key=priv, auth_secret=auth, version="aes128gcm")
        self.assertEqual(json.loads(plain.decode()),
                         {"title": "Ratatoskr", "body": "verzendtest", "url": "/"})


if __name__ == "__main__":
    unittest.main()
