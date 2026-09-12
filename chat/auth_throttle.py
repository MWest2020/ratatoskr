# SPDX-License-Identifier: EUPL-1.2
"""De rem op inlogpogingen.

Een self-hosted installatie heeft geen WAF voor zich staan, dus de rem hoort in
de app. Oplopende wachttijd per sleutel — dat is de gebruikersnaam én de bron,
elk apart: één account platleggen lukt dan niet door vanaf één adres te rammen,
en één adres blokkeren niet door namen te raden.

Deelt de tabel `pogingen` met auth_store; een los bestand omdat het een eigen
zorg is (en omdat auth_store anders over de 200 regels uit CLAUDE.md gaat).
"""
from auth_store import _connect, now

def blocked_for(key):
    """Seconden die deze sleutel nog moet wachten (0 = mag)."""
    with _connect() as con:
        row = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (key,)).fetchone()
        return max(0, row["tot"] - now()) if row else 0


def note_failure(key, wait_from=3, max_wait=300):
    """Tel de mislukking en zet de wachttijd. Oplopend, met een plafond."""
    with _connect() as con:
        row = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (key,)).fetchone()
        count = (row["aantal"] if row else 0) + 1
        wait = 0 if count < wait_from else min(2 ** (count - wait_from), max_wait)
        con.execute("INSERT OR REPLACE INTO pogingen (sleutel, aantal, tot) VALUES (?,?,?)",
                    (key, count, now() + wait))


def clear_attempts(key):
    with _connect() as con:
        con.execute("DELETE FROM pogingen WHERE sleutel = ?", (key,))
