#!/usr/bin/env python3
"""Boomhuis chat backend — HTTP routing plus static PWA assets.

Thin: the buzz/relay data layer lives in buzzcli.py, the GitHub read layer in
github.py, the read routes in read_routes.py. Here only the serving of the PWA
shell, the session gate, and the write routes.
"""
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import push    # Web Push — subscription storage
from buzzcli import buzz_admin, valid_cid
import actions  # send/add-member/create actions (the server stays thin)
import auth          # sessions, cookies, invitations
import auth_admin    # inviting and the second factor (behind the session)
import auth_routes   # logging in, setup, using an invite, and the gate
import read_routes   # the GET routes under /api/ that read data
import settings      # RATATOSKR_*/BOOMHUIS_* from the environment
import statics       # the allowlist of files we serve

HERE = os.path.dirname(os.path.abspath(__file__))


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        # HEAD krijgt dezelfde headers en geen body. Dat is niet alleen de HTTP-
        # regel: zonder dit gaf elke HEAD een 501 met een HTML-foutpagina, en die
        # `content-type: text/html` liet mij op 2026-09-13 bijna concluderen dat
        # het manifest verkeerd geserveerd werd. Een diagnosemiddel dat over zijn
        # eigen voeten struikelt is erger dan geen diagnosemiddel.
        if self.command != "HEAD":
            self.wfile.write(data)
        self._log_access(code)

    def log_message(self, *a):  # quiet: our own line below is enough
        pass

    def _log_access(self, code):
        """One line per request to stdout (journald), when RATATOSKR_ACCESSLOG is
        on.

        Exists to answer one question you cannot see from outside: does an
        installed PWA actually fetch the new files? Only method, path, status and
        a truncated user agent — no headers, no tokens, no bodies.
        """
        if settings.read("ACCESSLOG") not in ("1", "true", "yes"):
            return
        ua = (self.headers.get("User-Agent") or "-")[:80].replace("\n", " ")
        print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} "
              f"{self.command} {self.path[:120]} {code} \"{ua}\"", flush=True)

    def do_GET(self):
        u = urlparse(self.path)
        # The login page comes before the gate: otherwise you can never log in.
        if u.path == "/login":
            with open(os.path.join(HERE, "login.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if statics.serve(self, u.path):
            return None
        if u.path.startswith("/api/"):
            # Reading sits behind the session too: these routes carry channel
            # names, messages and agent traffic. Without a tailnet in front,
            # "reading is open" simply means "everything is public".
            if u.path == "/api/status":
                return auth_routes.status(self)
            if u.path == "/api/sessie":
                return auth_routes.session_info(self)
            if auth_routes.gate(self, u.path, writes=False) is None:
                return None

        if read_routes.route(self, u):
            return None
        return self._send(404, json.dumps({"error": "not found"}))

    def do_HEAD(self):
        # Dezelfde route als GET; _send laat de body weg.
        return self.do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._send(400, json.dumps({"error": "bad length"}))
        # Hard ceiling: no POST body (send, subscribe) is large; this stops a
        # tailnet node from making the backend read without limit.
        if n < 0 or n > 16384:
            return self._send(413, json.dumps({"error": "body too large"}))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad json"}))

        # Logging in, setup and using an invitation cannot have a session by
        # definition; those go before the gate.
        if auth_routes.open_route(self, u.path, body):
            return None
        if u.path == "/api/uitloggen":
            return auth_routes.log_out(self, body)

        # Everything else: a session plus a session-bound token, because every
        # POST changes something (message, channel, member, push, invitation).
        session = auth_routes.gate(self, u.path, writes=True)
        if session is None:
            return None
        if auth_admin.route(self, u.path, session, body):
            return None

        if u.path == "/api/push/subscribe":
            if push.add_subscription(body):
                return self._send(200, json.dumps({"ok": True}))
            return self._send(400, json.dumps({"error": "invalid subscription"}))

        if u.path == "/api/channels/create":
            code, payload = actions.create_channel(body.get("name"))
            return self._send(code, json.dumps(payload))

        if u.path == "/api/channels/delete":
            cid = body.get("channel")
            if not valid_cid(cid):
                return self._send(400, json.dumps({"error": "unknown channel"}))
            # Deleting is channel management: signs as orchestrator, not as mark.
            rc, out, err = buzz_admin(["channels", "delete", "--channel", cid])
            if rc is None:
                return self._send(503, json.dumps({"error": err}))
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            return self._send(200, json.dumps({"ok": True}))

        if u.path == "/api/channel/add-member":
            code, payload = actions.add_agent(body.get("channel"), body.get("name"))
            return self._send(code, json.dumps(payload))

        if u.path != "/api/send":
            return self._send(404, json.dumps({"error": "not found"}))
        code, payload = actions.send(body.get("channel"), body.get("content"),
                                     force=bool(body.get("force")))
        return self._send(code, json.dumps(payload))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    # The bind host is config, not code. Default 0.0.0.0 (unchanged behaviour); on
    # the relay VM we set BIND_HOST to the tailnet IP (100.x) so the port does not
    # listen on the LAN interface — then only a tailnet node can post.
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    auth_routes.print_setup_link_at_start()
    print(f"[chat] listening on {host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()
