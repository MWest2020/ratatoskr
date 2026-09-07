# SPDX-License-Identifier: EUPL-1.2
"""HTTP-routing: een ECHTE server op localhost, met de relay- en GitHub-laag
gestubd. Geen mock van de handler zelf, want juist de routing en de volgorde van
de checks zijn wat hier misging.

De invariant die deze tests bewaken: **lezen is open, elke POST loopt eerst langs
het apparaat-token**, en er komt nooit een rauwe upstream-fout terug op een
invoerfout van de gebruiker.
"""
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["BOOMHUIS_APP_TOKEN"] = "geheim"

import buzzcli   # noqa: E402  — na het zetten van de env
import github    # noqa: E402
import push      # noqa: E402
import server    # noqa: E402

CID = "11111111-2222-3333-4444-555555555555"


def _stub():
    buzzcli.list_channels = lambda: [("general", CID)]
    buzzcli.valid_cid = lambda c: c == CID
    server.valid_cid = buzzcli.valid_cid
    server.list_channels_meta = lambda: [{"name": "general", "id": CID, "description": "hub"}]
    server.agent_roster = lambda: [{"handle": "odin", "pubkey": "pk", "rol": "meta-agent"}]
    server.channel_roster = lambda: {"general": ["odin"]}
    server.channel_overview = lambda: [{"name": "general", "id": CID, "count": 1}]
    server.author = lambda pk: "odin"
    server.buzz = lambda args, stdin=None, timeout=25, key=None: (
        0, json.dumps([{"id": "m1", "pubkey": "pk", "content": "hoi", "created_at": 2},
                       {"id": "m0", "pubkey": "pk", "content": "eerder", "created_at": 1}]), "")
    server.buzz_admin = lambda args, stdin=None, timeout=25: (0, "{}", "")
    server.actions.buzz = server.buzz
    server.actions.buzz_admin = server.buzz_admin
    server.actions.valid_cid = buzzcli.valid_cid
    github.list_repos = lambda limit=30: [{"full_name": "MWest2020/x"}]
    github.list_prs = lambda full: [{"number": 1}]
    github.get_pr = lambda full, n: {"number": n}
    github.get_file = lambda p: "# pin"
    push.vapid_public = lambda: "vapid"
    push.add_subscription = lambda s: True


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _stub()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, pad, data=None, token=None, raw=None):
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(self.base + pad, data=body,
                                     method="POST" if body is not None else "GET")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-App-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    # --- lezen is open ---
    def test_leesroutes_zonder_token(self):
        for pad in ("/api/channels", "/api/agents", "/api/channel-members",
                    "/api/push/vapid", "/api/overview", "/api/repos",
                    f"/api/messages?channel={CID}", "/api/pinned?channel=general"):
            self.assertEqual(self.call(pad)[0], 200, pad)

    def test_shell_wordt_geserveerd(self):
        for pad in ("/", "/index.html", "/app.js", "/app-repos.js", "/sw.js"):
            code, body = self.call(pad)
            self.assertEqual(code, 200, pad)
            self.assertTrue(body.strip(), pad)

    def test_onbekend_pad_is_404(self):
        self.assertEqual(self.call("/bestaat-niet")[0], 404)

    def test_berichten_komen_op_tijd_gesorteerd(self):
        _, body = self.call(f"/api/messages?channel={CID}")
        ts = [m["ts"] for m in json.loads(body)["messages"]]
        self.assertEqual(ts, sorted(ts))

    def test_onbekend_kanaal_is_400_geen_502(self):
        self.assertEqual(self.call("/api/messages?channel=nope")[0], 400)

    def test_repo_parameter_wordt_gevalideerd(self):
        self.assertEqual(self.call("/api/prs?repo=MWest2020/x")[0], 200)
        for slecht in ("", "zonder-owner", "../etc", "a/b/c"):
            self.assertEqual(self.call("/api/prs?repo=" + slecht)[0], 400, slecht)
        self.assertEqual(self.call("/api/pr?repo=MWest2020/x&num=abc")[0], 400)

    def test_pinned_met_raar_kanaal_geeft_leeg_niet_stuk(self):
        code, body = self.call("/api/pinned?channel=../../etc")
        self.assertEqual((code, json.loads(body)), (200, {"content": ""}))

    # --- schrijven gaat eerst langs de poort ---
    def test_elke_post_zonder_token_is_401(self):
        for pad in ("/api/send", "/api/channels/create", "/api/channels/delete",
                    "/api/channel/add-member", "/api/push/subscribe", "/api/onbekend"):
            code, body = self.call(pad, data={})
            self.assertEqual(code, 401, pad)
            self.assertIn("apparaat-token", body)

    def test_verkeerd_token_is_ook_401(self):
        self.assertEqual(self.call("/api/send", data={}, token="fout")[0], 401)

    def test_met_token_komt_de_route_wel_aan_bod(self):
        code, _ = self.call("/api/send", data={"channel": CID, "content": "hoi"}, token="geheim")
        self.assertEqual(code, 200)

    def test_onbekende_postroute_met_token_is_404(self):
        self.assertEqual(self.call("/api/onbekend", data={}, token="geheim")[0], 404)

    def test_te_grote_body_wordt_geweigerd(self):
        self.assertEqual(self.call("/api/send", raw=b"x" * 20000, token="geheim")[0], 413)

    def test_kapotte_json_is_400_geen_traceback(self):
        self.assertEqual(self.call("/api/send", raw=b"{geen json", token="geheim")[0], 400)

    def test_antwoorden_worden_niet_gecachet(self):
        with urllib.request.urlopen(self.base + "/api/channels", timeout=10) as r:
            self.assertEqual(r.headers.get("Cache-Control"), "no-store")


if __name__ == "__main__":
    unittest.main()
