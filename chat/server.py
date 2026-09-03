#!/usr/bin/env python3
"""Boomhuis chat-backend — HTTP-routing + statische PWA-assets.

Dun: de buzz/relay-datalaag zit in buzzcli.py, de GitHub-leeslaag in github.py.
Hier alleen het serveren van de PWA-shell en de /api/*-routes.
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import github  # GitHub-leeslaag (repo/PR-view + pinned-context)
import push    # Web Push — subscription-opslag + VAPID-public-key
from buzzcli import (buzz, list_channels, list_channels_meta, valid_cid, author,
                     channel_overview, agent_roster, channel_roster, ME)
import roster  # naam↔pubkey-resolutie voor de 'agent toevoegen'-flow

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

    def log_message(self, *a):  # stil
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        # PWA-assets (app-shell). sw.js op root-scope zodat de worker de hele
        # app kan controleren.
        static = {
            "/app.css": ("app.css", "text/css"),
            "/app.js": ("app.js", "text/javascript"),
            "/app-ui.js": ("app-ui.js", "text/javascript"),
            "/app-push.js": ("app-push.js", "text/javascript"),
            "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
            "/sw.js": ("sw.js", "text/javascript"),
            "/icon.svg": ("icon.svg", "image/svg+xml"),
            "/icon-192.png": ("icon-192.png", "image/png"),
            "/icon-512.png": ("icon-512.png", "image/png"),
            "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
        }
        if u.path in static:
            fname, ctype = static[u.path]
            try:
                with open(os.path.join(HERE, fname), "rb") as f:
                    return self._send(200, f.read(), ctype)
            except OSError:
                return self._send(404, json.dumps({"error": "asset weg"}))
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
            if not repo:
                return self._send(400, json.dumps({"error": "repo ontbreekt"}))
            try:
                return self._send(200, json.dumps({"prs": github.list_prs(repo)}))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/pr":
            q = parse_qs(u.query)
            repo = (q.get("repo") or [""])[0]
            num = (q.get("num") or [""])[0]
            if not repo or not num.isdigit():
                return self._send(400, json.dumps({"error": "repo/num ontbreekt"}))
            try:
                return self._send(200, json.dumps(github.get_pr(repo, int(num))))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)[:200]}))
        if u.path == "/api/pinned":
            # Pinned context = knowledge/<kanaal>.md uit de boomhuis-repo (één bron
            # van waarheid; update via git push). Leeg = geen pin.
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
        # Harde bovengrens: geen enkele POST-body (send, subscribe) is groot; dit
        # voorkomt dat een tailnet-node de backend ongelimiteerd laat lezen.
        if n < 0 or n > 16384:
            return self._send(413, json.dumps({"error": "body te groot"}))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad json"}))

        if u.path == "/api/push/subscribe":
            if push.add_subscription(body):
                return self._send(200, json.dumps({"ok": True}))
            return self._send(400, json.dumps({"error": "ongeldige subscription"}))

        if u.path == "/api/channels/create":
            name = (body.get("name") or "").strip().lower()
            if not re.match(r"^[a-z0-9][a-z0-9_-]{0,30}$", name):
                return self._send(400, json.dumps({"error": "naam: a-z 0-9 _ - (max 31)"}))
            rc, out, err = buzz(["channels", "create", "--name", name,
                                 "--type", "stream", "--visibility", "open"])
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            # Beleid: coordinator zit in ELK kanaal → standaard toevoegen aan een nieuw
            # kanaal. Best-effort: mislukt dit, dan bestaat het kanaal nog steeds
            # (coordinator kan later handmatig of via de mention-pop-up toegevoegd).
            try:
                new_cid = json.loads(out).get("channel_id")
                co = roster.pubkey_of("coordinator")
                if new_cid and co:
                    buzz(["channels", "add-member", "--channel", new_cid,
                          "--pubkey", co, "--role", "bot"])
            except Exception:
                pass
            return self._send(200, json.dumps({"ok": True, "name": name}))

        if u.path == "/api/channels/delete":
            cid = body.get("channel")
            if not valid_cid(cid):
                return self._send(400, json.dumps({"error": "onbekend kanaal"}))
            rc, out, err = buzz(["channels", "delete", "--channel", cid])
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            return self._send(200, json.dumps({"ok": True}))

        if u.path == "/api/channel/add-member":
            return self._add_member(body)

        if u.path != "/api/send":
            return self._send(404, json.dumps({"error": "not found"}))
        cid, content = body.get("channel"), (body.get("content") or "").strip()
        if not valid_cid(cid):
            return self._send(400, json.dumps({"error": "onbekend kanaal"}))
        if not content:
            return self._send(400, json.dumps({"error": "leeg bericht"}))
        # Geen geforceerde --mention: de relay resolvet @agent naar het lid en
        # triggert 'm; een @naam die GEEN kanaal-lid is geeft een nette fout die de
        # naam noemt. Die vangen we op als een 'agent-niet-in-kanaal'-antwoord voor
        # de toevoeg-pop-up (content via stdin om escaping te vermijden).
        rc, out, err = buzz(["messages", "send", "--channel", cid, "--content", "-"],
                            stdin=content)
        if rc == 0:
            return self._send(200, json.dumps({"ok": True}))
        m = re.search(r"mention '@([A-Za-z0-9_-]+)' does not match", err or "")
        if m:
            who = m.group(1)
            return self._send(409, json.dumps({
                "missing_agent": who,
                "known": roster.pubkey_of(who) is not None,  # bestaat 'ie als identiteit?
                "channel": cid}))
        return self._send(502, json.dumps({"error": err.strip()[:200]}))

    def _add_member(self, body):
        cid, name = body.get("channel"), (body.get("name") or "").strip()
        if not valid_cid(cid):
            return self._send(400, json.dumps({"error": "onbekend kanaal"}))
        pk = roster.pubkey_of(name)
        if not pk:
            return self._send(404, json.dumps({"error": f"geen identiteit '{name}'"}))
        rc, out, err = buzz(["channels", "add-member", "--channel", cid,
                             "--pubkey", pk, "--role", "bot"])
        if rc != 0:
            return self._send(502, json.dumps({"error": (err or out).strip()[:200]}))
        return self._send(200, json.dumps({"ok": True, "name": name}))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    # Bind-host is config, niet code. Default 0.0.0.0 (ongewijzigd gedrag); op de
    # relay-VM zetten we BIND_HOST op het tailnet-IP (100.x) zodat de poort niet
    # op de LAN-interface luistert — dan kan alleen een tailnet-node posten.
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    print(f"[chat] luistert op {host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()
