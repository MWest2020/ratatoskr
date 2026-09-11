# SPDX-License-Identifier: EUPL-1.2
"""HTTP-routing: een ECHTE server op localhost, met de relay- en GitHub-laag
gestubd. Geen mock van de handler zelf, want juist de routing en de volgorde van
de checks zijn wat hier misging.

De invariant die deze tests bewaken: **niets is open behalve de inlogroutes en
de shell; elk verzoek onder /api/ vereist een sessie, en elke POST daarbovenop
een sessiegebonden token**. En er komt nooit een rauwe upstream-fout terug op
een invoerfout van de gebruiker.

Lezen was ooit open omdat het tailnet het afschermde. Sinds
`inloggen-per-persoon` niet meer: in die routes staan kanaalnamen, berichten en
agent-verkeer.
"""
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import tempfile

os.environ["BOOMHUIS_AUTH_DB"] = os.path.join(tempfile.mkdtemp(), "auth.db")
os.environ.pop("BOOMHUIS_APP_TOKEN", None)

import auth      # noqa: E402  — na het zetten van de env
import auth_store as store  # noqa: E402
import buzzcli   # noqa: E402
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
        pid = store.maak_persoon("tester", auth.hash_wachtwoord("een goed wachtwoord"))
        cls.sessie, cls.csrf = auth.start_sessie(pid)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, pad, data=None, raw=None, sessie=True, csrf=True):
        """`sessie=False` doet alsof je niet ingelogd bent, `csrf=False` alsof
        het sessietoken ontbreekt — de twee manieren waarop een verzoek hoort
        te stranden."""
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(self.base + pad, data=body,
                                     method="POST" if body is not None else "GET")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if sessie:
            req.add_header("Cookie", "{}={}".format(auth.COOKIE, self.sessie))
        if body is not None and csrf:
            req.add_header(auth.CSRF_HEADER, self.csrf)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    # --- Android-app ---
    def test_assetlinks_is_open(self):
        """Chrome haalt dit op vóór er een gebruiker is; achter de sessie zou de
        app altijd met een adresbalk starten."""
        code, body = self.call("/.well-known/assetlinks.json", sessie=False)
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertEqual(d[0]["target"]["namespace"], "android_app")
        self.assertTrue(d[0]["target"]["sha256_cert_fingerprints"][0].count(":") == 31,
                        "vingerafdruk hoort 32 hex-paren te zijn")

    def test_apk_zit_achter_de_sessie(self):
        code, _ = self.call("/ratatoskr.apk", sessie=False)
        self.assertEqual(code, 401)

    def test_apk_zonder_bestand_is_404_geen_500(self):
        """Een installatie zonder app hoort netjes te zeggen dat hij er niet is."""
        code, body = self.call("/ratatoskr.apk")
        self.assertIn(code, (200, 404))
        if code == 404:
            self.assertIn("geen app", body)

    # --- lezen zit achter de sessie ---
    LEESROUTES = ("/api/channels", "/api/agents", "/api/channel-members",
                  "/api/push/vapid", "/api/overview", "/api/repos",
                  f"/api/messages?channel={CID}", "/api/pinned?channel=general")

    def test_leesroutes_met_sessie(self):
        for pad in self.LEESROUTES:
            self.assertEqual(self.call(pad)[0], 200, pad)

    def test_leesroutes_zonder_sessie_zijn_401(self):
        for pad in self.LEESROUTES:
            code, body = self.call(pad, sessie=False)
            self.assertEqual(code, 401, pad)
            self.assertNotIn("general", body, pad)   # geen gegevens in het antwoord

    def test_de_shell_blijft_open(self):
        """De pagina en zijn scripts bevatten niets geheims, en de inlogpagina
        moet zonder sessie te laden zijn — anders kun je nooit inloggen."""
        for pad in ("/", "/login", "/app.js", "/login.js", "/sw.js"):
            self.assertEqual(self.call(pad, sessie=False)[0], 200, pad)

    def test_status_zegt_alleen_of_er_al_iemand_is(self):
        code, body = self.call("/api/status", sessie=False)
        self.assertEqual(code, 200)
        self.assertEqual(sorted(json.loads(body)), ["personen"])

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
    SCHRIJFROUTES = ("/api/send", "/api/channels/create", "/api/channels/delete",
                     "/api/channel/add-member", "/api/push/subscribe", "/api/onbekend")

    def test_elke_post_zonder_sessie_is_401(self):
        for pad in self.SCHRIJFROUTES:
            code, body = self.call(pad, data={}, sessie=False)
            self.assertEqual(code, 401, pad)
            self.assertIn("inloggen", body, pad)

    def test_elke_post_zonder_sessietoken_is_403(self):
        for pad in self.SCHRIJFROUTES:
            code, _ = self.call(pad, data={}, csrf=False)
            self.assertEqual(code, 403, pad)

    def test_met_sessie_komt_de_route_wel_aan_bod(self):
        code, _ = self.call("/api/send", data={"channel": CID, "content": "hoi"})
        self.assertEqual(code, 200)

    def test_onbekende_postroute_is_404(self):
        self.assertEqual(self.call("/api/onbekend", data={})[0], 404)

    def test_inloggen_kan_zonder_sessie(self):
        code, body = self.call("/api/login", data={"naam": "tester",
                                                   "wachtwoord": "fout"}, sessie=False)
        self.assertEqual(code, 401)
        self.assertIn("mislukt", body)

    def test_te_grote_body_wordt_geweigerd(self):
        self.assertEqual(self.call("/api/send", raw=b"x" * 20000)[0], 413)

    def test_kapotte_json_is_400_geen_traceback(self):
        self.assertEqual(self.call("/api/send", raw=b"{geen json")[0], 400)

    def test_antwoorden_worden_niet_gecachet(self):
        req = urllib.request.Request(self.base + "/api/channels")
        req.add_header("Cookie", "{}={}".format(auth.COOKIE, self.sessie))
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.headers.get("Cache-Control"), "no-store")


if __name__ == "__main__":
    unittest.main()
