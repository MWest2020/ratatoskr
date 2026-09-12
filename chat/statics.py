# SPDX-License-Identifier: EUPL-1.2
"""The files we serve — an allowlist, not a directory.

An allowlist because serving a directory means every file that ever lands in it
by accident (a .env, a key, a backup) is public at once. The price is that you
have to add a new file here; that was forgotten twice and then gave a 404 that
looked like something else. Hence this file of its own, with the list in one
place.

sw.js sits at root scope so the service worker can control the whole app.
"""
import json
import os

import settings

HERE = os.path.dirname(os.path.abspath(__file__))
# Where the Android app lives. NOT in the image: an APK is per installation (it
# is signed for one origin), so it belongs with the state, not with the code. An
# empty or missing directory = the route simply does not exist.
APK_DIR = settings.read("APK_DIR", "/var/lib/ratatoskr/apk")
APK_NAME = "ratatoskr.apk"

FILES = {
    "/app.css": ("app.css", "text/css"),
    "/board.css": ("board.css", "text/css"),
    "/app.js": ("app.js", "text/javascript"),
    "/app-cache.js": ("app-cache.js", "text/javascript"),
    "/app-connection.js": ("app-connection.js", "text/javascript"),
    "/app-auth.js": ("app-auth.js", "text/javascript"),
    "/login.js": ("login.js", "text/javascript"),
    "/app-modal.js": ("app-modal.js", "text/javascript"),
    "/app-ui.js": ("app-ui.js", "text/javascript"),
    "/app-repos.js": ("app-repos.js", "text/javascript"),
    "/app-board.js": ("app-board.js", "text/javascript"),
    "/app-push.js": ("app-push.js", "text/javascript"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/sw.js": ("sw.js", "text/javascript"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
    # Android app: Chrome fetches this BEFORE there is a user. Statics sit in
    # server.py before the session gate and this path does not start with /api/,
    # so it is open — and it has to be. If the fingerprint does not match the key
    # the APK was signed with, the app starts WITH an address bar: visibly wrong,
    # not silently.
    "/.well-known/assetlinks.json": ("well-known/assetlinks.json", "application/json"),
}


def serve_apk(h):
    """Serve the Android app — without a session, see server.py for why. Returns
    True when something was sent."""
    path = os.path.join(APK_DIR, APK_NAME)
    try:
        with open(path, "rb") as f:
            content = f.read()
    except OSError:
        return h._send(404, json.dumps({"error": "geen app geïnstalleerd op deze server"})) or True
    h._send(200, content, "application/vnd.android.package-archive")
    return True


def serve(h, path):
    """True when this path is a known file and has been sent."""
    if path not in FILES:
        return False
    name, ctype = FILES[path]
    try:
        with open(os.path.join(HERE, name), "rb") as f:
            return h._send(200, f.read(), ctype) or True
    except OSError:
        return h._send(404, json.dumps({"error": "asset weg"})) or True
