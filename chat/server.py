#!/usr/bin/env python3
"""Boomhuis chat — mobiele webinterface op de relay, via buzz-cli.

De nsec (identiteit 'mark') zit in de omgeving van dit proces, nooit in de
browser. De browser praat alleen met deze backend; de backend tekent via
buzz-cli. Tailnet-only (bind op het VM-IP, bereikbaar via de .60-route).
"""
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BUZZ = os.environ.get("BUZZ_BIN", "/usr/local/bin/buzz")
HERE = os.path.dirname(os.path.abspath(__file__))

# Kanalen (naam -> id). Bron van waarheid: boomhuis/channels.yml.
CHANNELS = [
    ("runs", "74504227-8f82-42d5-b943-e0bc059778bc"),
    ("escalatie", "c1a0db51-3c96-46f9-9afa-1f03acfd87a3"),
    ("bouw", "69cf0949-f1ab-4383-9627-8ef0f51977e1"),
    ("review", "b829eac4-a49b-4336-813e-90cdfa1a81c7"),
    ("architectuur", "1ed0e697-7187-43ae-b0a1-faa667e1c93e"),
    ("marketing", "b3b40816-ed50-4983-977b-44a3f8e9271f"),
]
CHANNEL_IDS = {cid for _, cid in CHANNELS}

# pubkey -> weergavenaam
NAMES = {
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
}
ME = "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db"
# handle -> pubkey, voor @mention-resolutie bij het posten
HANDLES = {"assistent": "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255"}


def buzz(args, stdin=None, timeout=25):
    p = subprocess.run([BUZZ, *args], capture_output=True, text=True,
                       input=stdin, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def author(pubkey):
    return NAMES.get(pubkey) or ("npub:" + pubkey[:8])


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
        if u.path == "/api/channels":
            return self._send(200, json.dumps(
                [{"name": n, "id": i} for n, i in CHANNELS]))
        if u.path == "/api/messages":
            cid = (parse_qs(u.query).get("channel") or [""])[0]
            if cid not in CHANNEL_IDS:
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
        if u.path != "/api/send":
            return self._send(404, json.dumps({"error": "not found"}))
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad json"}))
        cid, content = body.get("channel"), (body.get("content") or "").strip()
        if cid not in CHANNEL_IDS:
            return self._send(400, json.dumps({"error": "onbekend kanaal"}))
        if not content:
            return self._send(400, json.dumps({"error": "leeg bericht"}))
        # @handle -> pubkey injecteren zodat buzz de mention accepteert
        args = ["messages", "send", "--channel", cid, "--content", "-"]
        for handle, pub in HANDLES.items():
            if ("@" + handle).lower() in content.lower():
                args += ["--mention", pub]
        # content via stdin (--content -) om shell/escaping-problemen te vermijden
        rc, out, err = buzz(args, stdin=content)
        if rc != 0:
            return self._send(502, json.dumps({"error": err.strip()[:200]}))
        return self._send(200, json.dumps({"ok": True}))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
