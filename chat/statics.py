# SPDX-License-Identifier: EUPL-1.2
"""De bestanden die we serveren — een allowlist, geen map.

Een allowlist omdat een directory serveren betekent dat elk bestand dat ooit
per ongeluk in deze map belandt (een .env, een sleutel, een back-up) meteen
publiek is. De prijs is dat je een nieuw bestand hier moet toevoegen; dat is
twee keer vergeten en gaf dan een 404 die op iets anders leek. Vandaar dit
eigen bestand, met de lijst op één plek.

sw.js staat op root-scope zodat de service worker de hele app kan controleren.
"""
import json
import os

import settings

HERE = os.path.dirname(os.path.abspath(__file__))
# Waar de Android-app staat. NIET in de image: een APK is per installatie
# (hij is ondertekend voor één origin), dus hij hoort bij de staat, niet bij de
# code. Leeg of leeg gebleven map = de route bestaat gewoon niet.
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
    # Android-app: Chrome haalt dit op VÓÓR er een gebruiker is. Statics staan
    # in server.py vóór de sessie-gate en dit pad begint niet met /api/, dus het
    # is open — en dat moet ook. Klopt de vingerafdruk niet met de sleutel
    # waarmee de APK ondertekend is, dan start de app mét adresbalk: zichtbaar
    # fout, niet stil.
    "/.well-known/assetlinks.json": ("well-known/assetlinks.json", "application/json"),
}


def serve_apk(h):
    """De Android-app aanbieden — zonder sessie, zie server.py voor waarom.
    Return True als er iets verstuurd is."""
    path = os.path.join(APK_DIR, APK_NAME)
    try:
        with open(path, "rb") as f:
            content = f.read()
    except OSError:
        return h._send(404, json.dumps({"error": "geen app geïnstalleerd op deze server"})) or True
    h._send(200, content, "application/vnd.android.package-archive")
    return True


def serve(h, path):
    """True wanneer dit pad een bekend bestand is en verstuurd is."""
    if path not in FILES:
        return False
    name, ctype = FILES[path]
    try:
        with open(os.path.join(HERE, name), "rb") as f:
            return h._send(200, f.read(), ctype) or True
    except OSError:
        return h._send(404, json.dumps({"error": "asset weg"})) or True
