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
import time
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
    # Een momentopname van het werk-overzicht, zodat /api/board echt iets serveert
    # in plaats van de 404 die een verse installatie geeft.
    path = os.path.join(tempfile.mkdtemp(), "board.json")
    with open(path, "w") as f:
        json.dump({"generated_at": time.time(), "columns": [], "cards": []}, f)
    server.board.PATH = path
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
        pid = store.create_person("tester", auth.hash_password("een goed wachtwoord"))
        cls.session, cls.csrf = auth.start_session(pid)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, data=None, raw=None, session=True, csrf=True):
        """`session=False` doet alsof je niet ingelogd bent, `csrf=False` alsof
        het sessietoken ontbreekt — de twee manieren waarop een verzoek hoort
        te stranden."""
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(self.base + path, data=body,
                                     method="POST" if body is not None else "GET")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if session:
            req.add_header("Cookie", "{}={}".format(auth.COOKIE, self.session))
        if body is not None and csrf:
            req.add_header(auth.CSRF_HEADER, self.csrf)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    # --- werk-overzicht ---
    def test_board_without_a_snapshot_is_404_with_an_explanation(self):
        """Een leeg bord moet te onderscheiden zijn van een kapotte producent."""
        old = server.board.PATH
        server.board.PATH = "/bestaat/niet/board.json"
        try:
            code, body = self.call("/api/board")
        finally:
            server.board.PATH = old
        self.assertEqual(code, 404)
        self.assertIn("hint", body)

    # --- Android-app ---
    def test_assetlinks_is_open(self):
        """Chrome haalt dit op vóór er een gebruiker is; achter de sessie zou de
        app altijd met een adresbalk starten."""
        code, body = self.call("/.well-known/assetlinks.json", session=False)
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertEqual(d[0]["target"]["namespace"], "android_app")
        self.assertTrue(d[0]["target"]["sha256_cert_fingerprints"][0].count(":") == 31,
                        "vingerafdruk hoort 32 hex-paren te zijn")

    def test_apk_is_open(self):
        """Een APK-download start vaak buiten de sessie (downloadmanager, een
        doorgestuurde link in een andere app) en draagt het cookie dan niet mee.
        Achter de gate is de link onbruikbaar precies wanneer je 'm nodig hebt;
        het bestand bevat niets geheims."""
        code, _ = self.call("/ratatoskr.apk", session=False)
        self.assertIn(code, (200, 404))
        self.assertNotEqual(code, 401)

    def test_apk_without_a_file_is_404_not_500(self):
        """Een installatie zonder app hoort netjes te zeggen dat hij er niet is."""
        code, body = self.call("/ratatoskr.apk")
        self.assertIn(code, (200, 404))
        if code == 404:
            self.assertIn("geen app", body)

    # --- lezen zit achter de sessie ---
    READ_ROUTES = ("/api/channels", "/api/agents", "/api/channel-members",
                  "/api/push/vapid", "/api/overview", "/api/repos", "/api/board",
                  f"/api/messages?channel={CID}", "/api/pinned?channel=general")

    def test_read_routes_with_a_session(self):
        for path in self.READ_ROUTES:
            self.assertEqual(self.call(path)[0], 200, path)

    def test_read_routes_without_a_session_are_401(self):
        for path in self.READ_ROUTES:
            code, body = self.call(path, session=False)
            self.assertEqual(code, 401, path)
            self.assertNotIn("general", body, path)  # geen gegevens in het antwoord

    def test_the_shell_stays_open(self):
        """De pagina en zijn scripts bevatten niets geheims, en de inlogpagina
        moet zonder sessie te laden zijn — anders kun je nooit inloggen."""
        for path in ("/", "/login", "/app.js", "/login.js", "/sw.js"):
            self.assertEqual(self.call(path, session=False)[0], 200, path)

    def test_status_only_says_whether_someone_exists(self):
        code, body = self.call("/api/status", session=False)
        self.assertEqual(code, 200)
        self.assertEqual(sorted(json.loads(body)), ["personen"])

    def test_shell_is_served(self):
        for path in ("/", "/index.html", "/app.js", "/app-repos.js", "/sw.js"):
            code, body = self.call(path)
            self.assertEqual(code, 200, path)
            self.assertTrue(body.strip(), path)

    def test_unknown_path_is_404(self):
        self.assertEqual(self.call("/bestaat-niet")[0], 404)

    def test_messages_come_sorted_by_time(self):
        _, body = self.call(f"/api/messages?channel={CID}")
        ts = [m["ts"] for m in json.loads(body)["messages"]]
        self.assertEqual(ts, sorted(ts))

    def test_unknown_channel_is_400_not_502(self):
        self.assertEqual(self.call("/api/messages?channel=nope")[0], 400)

    def test_the_repo_parameter_is_validated(self):
        self.assertEqual(self.call("/api/prs?repo=MWest2020/x")[0], 200)
        for bad in ("", "zonder-owner", "../etc", "a/b/c"):
            self.assertEqual(self.call("/api/prs?repo=" + bad)[0], 400, bad)
        self.assertEqual(self.call("/api/pr?repo=MWest2020/x&num=abc")[0], 400)

    def test_pinned_with_an_odd_channel_gives_empty_not_broken(self):
        code, body = self.call("/api/pinned?channel=../../etc")
        self.assertEqual((code, json.loads(body)), (200, {"content": ""}))

    # --- schrijven gaat eerst langs de poort ---
    WRITE_ROUTES = ("/api/send", "/api/channels/create", "/api/channels/delete",
                     "/api/channel/add-member", "/api/push/subscribe", "/api/onbekend")

    def test_every_post_without_a_session_is_401(self):
        for path in self.WRITE_ROUTES:
            code, body = self.call(path, data={}, session=False)
            self.assertEqual(code, 401, path)
            self.assertIn("inloggen", body, path)

    def test_every_post_without_a_session_token_is_403(self):
        for path in self.WRITE_ROUTES:
            code, _ = self.call(path, data={}, csrf=False)
            self.assertEqual(code, 403, path)

    def test_with_a_session_the_route_is_reached(self):
        code, _ = self.call("/api/send", data={"channel": CID, "content": "hoi"})
        self.assertEqual(code, 200)

    def test_unknown_post_route_is_404(self):
        self.assertEqual(self.call("/api/onbekend", data={})[0], 404)

    def test_logging_in_works_without_a_session(self):
        code, body = self.call("/api/login", data={"naam": "tester",
                                                   "wachtwoord": "fout"}, session=False)
        self.assertEqual(code, 401)
        self.assertIn("mislukt", body)

    def test_an_oversized_body_is_refused(self):
        self.assertEqual(self.call("/api/send", raw=b"x" * 20000)[0], 413)

    def test_broken_json_is_400_not_a_traceback(self):
        self.assertEqual(self.call("/api/send", raw=b"{geen json")[0], 400)

    def test_responses_are_not_cached(self):
        req = urllib.request.Request(self.base + "/api/channels")
        req.add_header("Cookie", "{}={}".format(auth.COOKIE, self.session))
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.headers.get("Cache-Control"), "no-store")


if __name__ == "__main__":
    unittest.main()
