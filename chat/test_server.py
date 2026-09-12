# SPDX-License-Identifier: EUPL-1.2
"""HTTP routing: a REAL server on localhost, with the relay and GitHub layers
stubbed. No mock of the handler itself, because the routing and the order of the
checks are exactly what went wrong here.

The invariant these tests guard: **nothing is open except the login routes and
the shell; every request under /api/ needs a session, and every POST needs a
session-bound token on top**. And a raw upstream error never comes back on a
user input error.

Reading was once open because the tailnet shielded it. Since
`inloggen-per-persoon` no longer: those routes carry channel names, messages and
agent traffic.
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

import auth      # noqa: E402  — after setting the env
import auth_store as store  # noqa: E402
import buzzcli   # noqa: E402
import github    # noqa: E402
import push      # noqa: E402
import read_routes  # noqa: E402
import server    # noqa: E402

CID = "11111111-2222-3333-4444-555555555555"


def _stub():
    buzzcli.list_channels = lambda: [("general", CID)]
    buzzcli.valid_cid = lambda c: c == CID
    server.valid_cid = read_routes.valid_cid = buzzcli.valid_cid
    read_routes.list_channels_meta = lambda: [{"name": "general", "id": CID, "description": "hub"}]
    read_routes.agent_roster = lambda: [{"handle": "odin", "pubkey": "pk", "rol": "meta-agent"}]
    read_routes.channel_roster = lambda: {"general": ["odin"]}
    read_routes.channel_overview = lambda: [{"name": "general", "id": CID, "count": 1}]
    read_routes.author = lambda pk: "odin"
    read_routes.buzz = lambda args, stdin=None, timeout=25, key=None: (
        0, json.dumps([{"id": "m1", "pubkey": "pk", "content": "hoi", "created_at": 2},
                       {"id": "m0", "pubkey": "pk", "content": "eerder", "created_at": 1}]), "")
    server.buzz_admin = lambda args, stdin=None, timeout=25: (0, "{}", "")
    server.actions.buzz = read_routes.buzz
    server.actions.buzz_admin = server.buzz_admin
    server.actions.valid_cid = buzzcli.valid_cid
    # A snapshot of the work overview, so /api/board really serves something
    # instead of the 404 a fresh installation gives.
    path = os.path.join(tempfile.mkdtemp(), "board.json")
    with open(path, "w") as f:
        json.dump({"generated_at": time.time(), "columns": [], "cards": []}, f)
    read_routes.board.PATH = path
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
        """`session=False` pretends you are not logged in, `csrf=False` that the
        session token is missing — the two ways a request should strand."""
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

    # --- work overview ---
    def test_board_without_a_snapshot_is_404_with_an_explanation(self):
        """An empty board must be distinguishable from a broken producer."""
        old = read_routes.board.PATH
        read_routes.board.PATH = "/bestaat/niet/board.json"
        try:
            code, body = self.call("/api/board")
        finally:
            read_routes.board.PATH = old
        self.assertEqual(code, 404)
        self.assertIn("hint", body)

    # --- Android app ---
    def test_assetlinks_is_open(self):
        """Chrome fetches this before there is a user; behind the session the app
        would always start with an address bar."""
        code, body = self.call("/.well-known/assetlinks.json", session=False)
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertEqual(d[0]["target"]["namespace"], "android_app")
        self.assertTrue(d[0]["target"]["sha256_cert_fingerprints"][0].count(":") == 31,
                        "a fingerprint should be 32 hex pairs")

    def test_apk_is_open(self):
        """An APK download often starts outside the session (download manager, a
        forwarded link in another app) and then does not carry the cookie. Behind
        the gate the link is useless exactly when you need it; the file holds
        nothing secret."""
        code, _ = self.call("/ratatoskr.apk", session=False)
        self.assertIn(code, (200, 404))
        self.assertNotEqual(code, 401)

    def test_apk_without_a_file_is_404_not_500(self):
        """An installation without an app should say cleanly that it is not there."""
        code, body = self.call("/ratatoskr.apk")
        self.assertIn(code, (200, 404))
        if code == 404:
            self.assertIn("no app", body)

    # --- reading sits behind the session ---
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
            self.assertNotIn("general", body, path)  # no data in the answer

    def test_the_shell_stays_open(self):
        """The page and its scripts hold nothing secret, and the login page has to
        load without a session — otherwise you can never log in."""
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

    # --- writing goes past the gate first ---
    WRITE_ROUTES = ("/api/send", "/api/channels/create", "/api/channels/delete",
                     "/api/channel/add-member", "/api/push/subscribe", "/api/onbekend")

    def test_every_post_without_a_session_is_401(self):
        for path in self.WRITE_ROUTES:
            code, body = self.call(path, data={}, session=False)
            self.assertEqual(code, 401, path)
            self.assertIn("sign-in required", body, path)

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
        self.assertIn("sign-in failed", body)

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
