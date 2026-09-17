# SPDX-License-Identifier: MIT
"""Tests for the 2026-09-12 security-review fixes on chat/auth_routes.py:
setup()'s race, the timing leak in log_in(), and X-Forwarded-For. Each test
here fails against the pre-fix code — see
handover/2026-09-12-security-review-auth.md for the findings (F1-F3).
"""
import os
import tempfile
import threading
import unittest

os.environ.setdefault("BOOMHUIS_AUTH_DB", os.path.join(tempfile.mkdtemp(), "auth.db"))

import auth  # noqa: E402
import auth_factors  # noqa: E402
import auth_routes as routes  # noqa: E402
import auth_store as store  # noqa: E402
from test_auth_routes import _Handler, _post  # noqa: E402


class SetupRace(unittest.TestCase):
    """F1: setup() only allows a first person — its own database, because by
    now the shared suite database already has people in it."""

    def setUp(self):
        self._old_path = store.PATH
        store.PATH = os.path.join(tempfile.mkdtemp(), "auth.db")

    def tearDown(self):
        store.PATH = self._old_path

    def test_two_concurrent_setups_yield_a_single_owner(self):
        token = auth.new_invite("setup")
        codes = []
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def attempt(name):
            barrier.wait()
            h = _post(routes.setup, {"token": token, "naam": name,
                                     "wachtwoord": "lang genoeg wachtwoord"})
            with lock:
                codes.append(h.code)

        threads = [threading.Thread(target=attempt, args=(n,))
                   for n in ("race-a", "race-b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(codes.count(201), 1)
        with store._connect() as con:
            owners = con.execute(
                "SELECT COUNT(*) c FROM personen WHERE eigenaar = 1").fetchone()["c"]
        self.assertEqual(owners, 1)


class UnknownNameCost(unittest.TestCase):
    """F2: an unknown name must cost the same one scrypt hash as a known one,
    not a fresh dummy hash on top of it."""

    def test_an_unknown_name_does_not_hash_a_fresh_dummy(self):
        calls = []
        original = auth_factors.hash_password

        def counting(*a, **kw):
            calls.append(1)
            return original(*a, **kw)

        auth_factors.hash_password = counting
        try:
            _post(routes.log_in, {"naam": "geen-mens-" + os.urandom(4).hex(),
                                  "wachtwoord": "iets"},
                 source="10.{}.{}.{}".format(*os.urandom(3)))
        finally:
            auth_factors.hash_password = original
        self.assertEqual(calls, [])


class Source(unittest.TestCase):
    """F3: X-Forwarded-For is only trusted from a loopback peer, and then
    only its last (proxy-appended) element."""

    def test_a_non_loopback_peer_is_not_overridden_by_the_header(self):
        h = _Handler({"X-Forwarded-For": "1.2.3.4"}, source="203.0.113.9")
        self.assertEqual(routes._source(h), "203.0.113.9")

    def test_a_loopback_peer_trusts_the_last_hop(self):
        h = _Handler({"X-Forwarded-For": "1.2.3.4, 10.0.0.7"}, source="127.0.0.1")
        self.assertEqual(routes._source(h), "10.0.0.7")


if __name__ == "__main__":
    unittest.main()
