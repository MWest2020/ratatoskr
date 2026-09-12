# SPDX-License-Identifier: EUPL-1.2
"""HTTP routing: a REAL server on localhost, with the relay and GitHub layers
stubbed. No mock of the handler itself, because the routing and the order of the
checks are exactly what went wrong here.

The invariant these tests guard: **nothing is open except the login routes and
the shell; every request under /api/ needs a session, and every POST needs a
session-bound token on top**. What the read routes answer past the gate is
tested in test_read_routes.py; the server itself is set up in live_server.py.

Reading was once open because the tailnet shielded it. Since
`inloggen-per-persoon` no longer: those routes carry channel names, messages and
agent traffic.
"""
import json
import unittest
import urllib.request

from live_server import CID, LiveServerCase, auth


class ServerTest(LiveServerCase):
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
