# SPDX-License-Identifier: EUPL-1.2
"""Schrijf-token voor de comms-API — de tweede laag onder de netwerklaag.

De backend hangt achter het tailnet (loopback-bind + `tailscale serve`), en dat
blijft de primaire control. Dit token dekt het geval dat het tailnet ooit een
node bevat die niet van Mark is: zonder token kun je dan wel meelezen, maar niet
schrijven — en schrijven is het gedrag dat zich als `mark` voordoet.

Leeg `BOOMHUIS_APP_TOKEN` = uit, gedrag ongewijzigd. Het token komt uit de
omgeving (`chat.env` op de VM), nooit uit git, en verschijnt nergens in een log
of antwoord.
"""
import hmac
import os

HEADER = "X-App-Token"


def required_token():
    """Het ingestelde token, of "" wanneer de deployment er geen zet."""
    return os.environ.get("BOOMHUIS_APP_TOKEN", "").strip()


def write_allowed(headers):
    """Mag dit verzoek schrijven? True wanneer er geen token is ingesteld, of
    wanneer de meegestuurde header er constant-time gelijk aan is."""
    want = required_token()
    if not want:
        return True
    got = headers.get(HEADER) or ""
    return hmac.compare_digest(got, want)
