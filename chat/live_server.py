# SPDX-License-Identifier: EUPL-1.2
"""A REAL chat server on localhost for the HTTP tests, with the relay and GitHub
layers stubbed. Not a test module itself: test_server.py (the gate) and
test_read_routes.py (what the read routes answer) both build on it.

The auth database is a temporary one: the env is set before auth is imported.
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
import auth_factors  # noqa: E402
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


class LiveServerCase(unittest.TestCase):
    """One server and one logged-in person per test class. Names are unique in
    the auth database, so a subclass that needs its own person sets PERSON."""
    PERSON = "tester"

    @classmethod
    def setUpClass(cls):
        _stub()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        pid = store.create_person(cls.PERSON, auth_factors.hash_password("een goed wachtwoord"))
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
