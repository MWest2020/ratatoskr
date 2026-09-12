#!/usr/bin/env python3
"""Boomhuis chat backend — HTTP routing plus static PWA assets.

Thin: the buzz/relay data layer lives in buzzcli.py, the GitHub read layer in
github.py. Here only the serving of the PWA shell and the /api/* routes.
"""
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import github  # GitHub read layer (repo/PR view + pinned context)
import push    # Web Push — subscription storage + VAPID public key
from buzzcli import (buzz, buzz_admin, list_channels, list_channels_meta, valid_cid, author,
                     channel_overview, agent_roster, channel_roster, ME)
import actions  # send/add-member/create actions (the server stays thin)
import auth          # sessions, passwords, TOTP
import board         # work overview (snapshot from jobs/board.py)
import auth_admin    # inviting and the second factor (behind the session)
import auth_routes   # logging in, setup, using an invite, and the gate
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
        if u.path == "/ratatoskr.apk":
            # Open, like /login and the asset links. Two reasons, both practical:
            # (a) an APK download often starts outside the session — a link you
            # forward opens in another app or in the download manager, and that
            # does not carry the cookie, so behind the gate the link is useless
            # exactly when you need it; (b) the file holds nothing secret: it is a
            # browser shell with the host name in it, and that is already in every
            # URL. The network layer (tailnet or proxy) is the door here.
            return statics.serve_apk(self) and None
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

        if u.path == "/api/channels":
            return self._send(200, json.dumps(list_channels_meta()))
        if u.path == "/api/agents":
            return self._send(200, json.dumps({"agents": agent_roster()}))
        if u.path == "/api/channel-members":
            try:
                return self._send(200, json.dumps({"channels": channel_roster()}))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/push/vapid":
            return self._send(200, json.dumps({"key": push.vapid_public()}))
        if u.path == "/api/board":
            payload, code = board.read()
            return self._send(code, json.dumps(payload))
        if u.path == "/api/overview":
            try:
                return self._send(200, json.dumps({"channels": channel_overview()}))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/repos":
            try:
                return self._send(200, json.dumps({"repos": github.list_repos()}))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/prs":
            repo = (parse_qs(u.query).get("repo") or [""])[0]
            if not github.valid_repo(repo):
                return self._send(400, json.dumps({"error": "repo: verwacht owner/naam"}))
            try:
                return self._send(200, json.dumps({"prs": github.list_prs(repo)}))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/pr":
            q = parse_qs(u.query)
            repo = (q.get("repo") or [""])[0]
            num = (q.get("num") or [""])[0]
            if not github.valid_repo(repo) or not num.isdigit():
                return self._send(400, json.dumps({"error": "repo: owner/naam, num: getal"}))
            try:
                return self._send(200, json.dumps(github.get_pr(repo, int(num))))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/pinned":
            # Pinned context = knowledge/<channel>.md from the boomhuis repo (one
            # source of truth; update through git push). Empty = no pin.
            name = (parse_qs(u.query).get("channel") or [""])[0].lower()
            if not re.match(r"^[a-z0-9][a-z0-9_-]{0,30}$", name):
                return self._send(200, json.dumps({"content": ""}))
            try:
                return self._send(200, json.dumps(
                    {"content": github.get_file(f"knowledge/{name}.md")}))
            except Exception:
                return self._send(200, json.dumps({"content": ""}))
        if u.path == "/api/messages":
            cid = (parse_qs(u.query).get("channel") or [""])[0]
            if not valid_cid(cid):
                return self._send(400, json.dumps({"error": "onbekend kanaal"}))
            rc, out, err = buzz(["messages", "get", "--channel", cid])
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            try:
                raw = json.loads(out)
            except Exception:
                raw = []
            msgs = raw if isinstance(raw, list) else raw.get("messages", [])
            out_msgs = [{
                "id": m.get("id"),
                "author": author(m.get("pubkey", "")),
                "mine": m.get("pubkey") == ME,
                "content": m.get("content", ""),
                "ts": m.get("created_at", 0),
            } for m in msgs]
            out_msgs.sort(key=lambda x: x["ts"])
            return self._send(200, json.dumps({"messages": out_msgs}))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._send(400, json.dumps({"error": "bad length"}))
        # Hard ceiling: no POST body (send, subscribe) is large; this stops a
        # tailnet node from making the backend read without limit.
        if n < 0 or n > 16384:
            return self._send(413, json.dumps({"error": "body te groot"}))
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
            return self._send(400, json.dumps({"error": "ongeldige subscription"}))

        if u.path == "/api/channels/create":
            code, payload = actions.create_channel(body.get("name"))
            return self._send(code, json.dumps(payload))

        if u.path == "/api/channels/delete":
            cid = body.get("channel")
            if not valid_cid(cid):
                return self._send(400, json.dumps({"error": "onbekend kanaal"}))
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
    print(f"[chat] luistert op {host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()
