# SPDX-License-Identifier: MIT
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

FILES = {
    "/app.css": ("app.css", "text/css"),
    "/header.css": ("header.css", "text/css"),
    "/repos.css": ("repos.css", "text/css"),
    "/board.css": ("board.css", "text/css"),
    "/login.css": ("login.css", "text/css"),
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
    "/app-update.js": ("app-update.js", "text/javascript"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/sw.js": ("sw.js", "text/javascript"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
}


def serve(h, path):
    """True when this path is a known file and has been sent."""
    if path not in FILES:
        return False
    name, ctype = FILES[path]
    try:
        with open(os.path.join(HERE, name), "rb") as f:
            return h._send(200, f.read(), ctype) or True
    except OSError:
        return h._send(404, json.dumps({"error": "asset missing"})) or True
