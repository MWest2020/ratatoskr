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

HERE = os.path.dirname(os.path.abspath(__file__))

BESTANDEN = {
    "/app.css": ("app.css", "text/css"),
    "/app.js": ("app.js", "text/javascript"),
    "/app-cache.js": ("app-cache.js", "text/javascript"),
    "/app-verbinding.js": ("app-verbinding.js", "text/javascript"),
    "/app-auth.js": ("app-auth.js", "text/javascript"),
    "/login.js": ("login.js", "text/javascript"),
    "/app-modal.js": ("app-modal.js", "text/javascript"),
    "/app-ui.js": ("app-ui.js", "text/javascript"),
    "/app-repos.js": ("app-repos.js", "text/javascript"),
    "/app-push.js": ("app-push.js", "text/javascript"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/sw.js": ("sw.js", "text/javascript"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
}


def serveer(h, pad):
    """True wanneer dit pad een bekend bestand is en verstuurd is."""
    if pad not in BESTANDEN:
        return False
    naam, ctype = BESTANDEN[pad]
    try:
        with open(os.path.join(HERE, naam), "rb") as f:
            return h._send(200, f.read(), ctype) or True
    except OSError:
        return h._send(404, json.dumps({"error": "asset weg"})) or True
