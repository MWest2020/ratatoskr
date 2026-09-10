# SPDX-License-Identifier: EUPL-1.2
"""De rem op inlogpogingen.

Een self-hosted installatie heeft geen WAF voor zich staan, dus de rem hoort in
de app. Oplopende wachttijd per sleutel — dat is de gebruikersnaam én de bron,
elk apart: één account platleggen lukt dan niet door vanaf één adres te rammen,
en één adres blokkeren niet door namen te raden.

Deelt de tabel `pogingen` met auth_store; een los bestand omdat het een eigen
zorg is (en omdat auth_store anders over de 200 regels uit CLAUDE.md gaat).
"""
from auth_store import _verbind, nu

def poging_geblokkeerd(sleutel):
    """Seconden die deze sleutel nog moet wachten (0 = mag)."""
    with _verbind() as con:
        rij = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (sleutel,)).fetchone()
        return max(0, rij["tot"] - nu()) if rij else 0


def noteer_mislukking(sleutel, wacht_vanaf=3, max_wacht=300):
    """Tel de mislukking en zet de wachttijd. Oplopend, met een plafond."""
    with _verbind() as con:
        rij = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (sleutel,)).fetchone()
        aantal = (rij["aantal"] if rij else 0) + 1
        wacht = 0 if aantal < wacht_vanaf else min(2 ** (aantal - wacht_vanaf), max_wacht)
        con.execute("INSERT OR REPLACE INTO pogingen (sleutel, aantal, tot) VALUES (?,?,?)",
                    (sleutel, aantal, nu() + wacht))


def wis_pogingen(sleutel):
    with _verbind() as con:
        con.execute("DELETE FROM pogingen WHERE sleutel = ?", (sleutel,))
