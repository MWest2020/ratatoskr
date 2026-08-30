#!/usr/bin/env python3
"""Boomhuis chat — mobiele webinterface op de relay, via buzz-cli.

De nsec (identiteit 'mark') zit in de omgeving van dit proces, nooit in de
browser. De browser praat alleen met deze backend; de backend tekent via
buzz-cli. Tailnet-only (bind op het VM-IP, bereikbaar via de .60-route).
"""
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BUZZ = os.environ.get("BUZZ_BIN", "/usr/local/bin/buzz")
HERE = os.path.dirname(os.path.abspath(__file__))

# Kanalen worden LIVE uit de relay gelezen (buzz channels list), zodat maken/
# verwijderen in de web-app meteen doorwerkt. #general staat vooraan.
def list_channels():
    rc, out, err = buzz(["channels", "list"])
    if rc != 0:
        return []
    try:
        d = json.loads(out)
    except Exception:
        return []
    c = d if isinstance(d, list) else d.get("channels", [])
    # De relay maakt zelf ondeletebare default-kanalen aan (een tweede 'general'
    # en 'welcome-everyone'); die filteren we weg. Voor 'general' houden we het
    # kanaal aan waar de agents in zitten.
    HIDE = {"welcome-everyone", "Welcome"}
    PREFER = {"general": "32ef5cd2-70d8-4b7e-9235-9692b8ab2a1c"}
    seen, rows = {}, []
    for x in c:
        name = x.get("name"); cid = x.get("channel_id") or x.get("id")
        if not name or not cid or name in HIDE:
            continue
        if name in PREFER and cid != PREFER[name]:
            continue  # sla het niet-voorkeurs-duplicaat over
        if name in seen:
            continue
        seen[name] = cid
        rows.append((name, cid))
    rows.sort(key=lambda r: (r[0] != "general", r[0]))  # general eerst, dan a-z
    return rows


def valid_cid(cid):
    return any(i == cid for _, i in list_channels())

# pubkey -> weergavenaam
NAMES = {
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
    "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49": "architect",
    "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74": "bouwer",
    "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64": "marketing",
}
ME = "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db"

# Bekende agents (uitbreidbaar: kopie met eigen identiteit + systemprompt).
AGENTS = [
    {"handle": "assistent",
     "pubkey": "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255",
     "rol": "algemene chat-agent"},
    {"handle": "architect",
     "pubkey": "a18ce524d234433a0702f85f09325165d19aa6fe5e9c28d01e22ffcf55922d49",
     "rol": "architectuur-sparring"},
    {"handle": "bouwer",
     "pubkey": "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74",
     "rol": "bouw-agent (habitat)"},
    {"handle": "marketing",
     "pubkey": "ba5bf9d6b4009984378561c35a346e64b488282ffd1fbc7dcdde1d19c515fd64",
     "rol": "marketing — usecases naar buiten"},
]


def buzz(args, stdin=None, timeout=25):
    p = subprocess.run([BUZZ, *args], capture_output=True, text=True,
                       input=stdin, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def author(pubkey):
    return NAMES.get(pubkey) or ("npub:" + pubkey[:8])


def channel_member_pubkeys(cid):
    rc, out, err = buzz(["channels", "members", "--channel", cid])
    if rc != 0:
        return {}
    try:
        d = json.loads(out)
    except Exception:
        return {}
    m = d if isinstance(d, list) else d.get("members", [])
    return {x.get("pubkey"): x.get("role") for x in m}


def agent_roster():
    """Per agent: in welke kanalen (naam) hij zit, met rol. Data uit buzz."""
    membership = {name: channel_member_pubkeys(cid) for name, cid in list_channels()}
    roster = []
    for a in AGENTS:
        chans = [name for name, mem in membership.items() if a["pubkey"] in mem]
        roster.append({"handle": a["handle"], "rol": a["rol"], "channels": chans})
    return roster


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
            return self._send(200, json.dumps(
                [{"name": n, "id": i} for n, i in list_channels()]))
        if u.path == "/api/agents":
            return self._send(200, json.dumps({"agents": agent_roster()}))
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
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad json"}))

        if u.path == "/api/channels/create":
            name = (body.get("name") or "").strip().lower()
            if not re.match(r"^[a-z0-9][a-z0-9_-]{0,30}$", name):
                return self._send(400, json.dumps({"error": "naam: a-z 0-9 _ - (max 31)"}))
            rc, out, err = buzz(["channels", "create", "--name", name,
                                 "--type", "stream", "--visibility", "open"])
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            return self._send(200, json.dumps({"ok": True, "name": name}))

        if u.path == "/api/channels/delete":
            cid = body.get("channel")
            if not valid_cid(cid):
                return self._send(400, json.dumps({"error": "onbekend kanaal"}))
            rc, out, err = buzz(["channels", "delete", "--channel", cid])
            if rc != 0:
                return self._send(502, json.dumps({"error": err.strip()[:200]}))
            return self._send(200, json.dumps({"ok": True}))

        if u.path != "/api/send":
            return self._send(404, json.dumps({"error": "not found"}))
        cid, content = body.get("channel"), (body.get("content") or "").strip()
        if not valid_cid(cid):
            return self._send(400, json.dumps({"error": "onbekend kanaal"}))
        if not content:
            return self._send(400, json.dumps({"error": "leeg bericht"}))
        # Altijd mark's eigen mention meegeven: dat staat elk @woord toe als
        # presentation-only (geen "geen kanaal-lid"-error meer), terwijl een
        # agent die WEL lid van dit kanaal is nog steeds uniek resolvet + getriggerd
        # wordt. Zo werkt @agent overal waar de agent woont, en faalt het nergens.
        args = ["messages", "send", "--channel", cid, "--content", "-",
                "--mention", ME]
        # content via stdin (--content -) om shell/escaping-problemen te vermijden
        rc, out, err = buzz(args, stdin=content)
        if rc != 0:
            return self._send(502, json.dumps({"error": err.strip()[:200]}))
        return self._send(200, json.dumps({"ok": True}))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    # Bind-host is config, niet code. Default 0.0.0.0 (ongewijzigd gedrag); op de
    # relay-VM zetten we BIND_HOST op het tailnet-IP (100.x) zodat de poort niet
    # op de LAN-interface luistert — dan kan alleen een tailnet-node posten.
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    print(f"[chat] luistert op {host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()
