#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Werk-overzicht: verzamel wat er loopt tot één momentopname (board.json).

Waarom een producent buiten de chat: de gegevens liggen niet waar de chat draait.
OpenSpec-changes staan in clones op deze host, werksessies als runbestanden in
/tmp, PR's bij GitHub. De chat-container is expres dependency-loos en serveert
alleen het bestand dat hier uit komt.

    python3 jobs/board.py > board.json     # of --out <pad>

Alles wat de kolom en de ouderdom bepaalt is PUUR (geen I/O), zodat het te
testen is zonder GitHub of een klok: zie jobs/test_board.py.
"""
import argparse
import glob
import json
import os
import subprocess
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DAY = 86400.0


def load_config(path=None):
    return yaml.safe_load(open(path or os.path.join(HERE, "board.yml")))


# --- puur: kolom en ouderdom -------------------------------------------------

def pr_column(pr):
    """In welke kolom hoort deze PR?

    Een draft is werk in uitvoering. Een OPEN, niet-draft PR wacht per definitie
    op een mens: in deze flow blijft hij staan tot iemand 'm merget. Gemerged is
    de uitgang.

    Waarom niet op `reviewDecision`: `gh search prs` kent dat veld niet (gemeten
    2026-09-12: "Unknown JSON field"). Dat per repo ophalen met `gh pr list` zou
    een aanroep per repo kosten voor een nuance die hier niets toevoegt — open
    en niet-draft ís hier wachten op review.
    """
    if pr.get("merged"):
        return "merged"
    return "building" if pr.get("draft") else "review"


def age_days(since, now):
    """Hoeveel dagen staat dit er al (nooit negatief — een klok die achterloopt
    mag geen kaart 'uit de toekomst' opleveren)."""
    return max(0.0, (now - float(since or now)) / DAY)


def is_stale(card, columns):
    """Staat deze kaart langer in zijn kolom dan de drempel? `stale_days: 0`
    betekent 'nooit muf' — dat is de uitgangskolom, daar mag alles liggen."""
    drempel = next((c.get("stale_days", 0) for c in columns if c["key"] == card["column"]), 0)
    return bool(drempel) and card["age_days"] > drempel


def summarise(cards, columns):
    """Per kolom: hoeveel kaarten, hoeveel daarvan muf. Het bord toont dit bovenaan
    zodat 'niets loopt vast' óók een zichtbare uitkomst is."""
    out = []
    for c in columns:
        inside = [k for k in cards if k["column"] == c["key"]]
        out.append({"key": c["key"], "title": c["title"],
                    "count": len(inside),
                    "stale": sum(1 for k in inside if k["stale"])})
    return out


# --- onzuiver: de bronnen ----------------------------------------------------

def openspec_cards(pattern, now):
    """Elke niet-gearchiveerde change is een voorstel. De ouderdom komt van de
    mtime van proposal.md — dat is wanneer er voor het laatst aan gewerkt is."""
    cards = []
    for path in glob.glob(pattern):
        if "/archive/" in path:
            continue
        change = os.path.basename(os.path.dirname(path))
        repo = path.split("/home/agent/", 1)[-1].split("/openspec/", 1)[0]
        try:
            ts = os.path.getmtime(path)
        except OSError:
            continue
        cards.append({"id": f"openspec:{repo}:{change}", "repo": repo,
                      "title": change, "column": "proposal",
                      "age_days": age_days(ts, now), "who": "", "url": "",
                      "source": path.replace("/home/agent/", "~/")})
    return cards


def gh_json(args):
    """`gh` aanroepen. Een fout is een LEESFOUT, geen lege lijst: stil niets
    tonen is niet te onderscheiden van 'er is niets', en dat is precies het
    verschil dat je wilt zien."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:160])
    return json.loads(p.stdout or "[]")


def pr_cards(owner, merged_days, now, ignore=()):
    velden = "repository,number,title,url,isDraft,updatedAt,author"
    rows = gh_json(["search", "prs", f"--owner={owner}", "--state=open",
                    "--limit", "40", "--json", velden])
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - merged_days * DAY))
    rows += [dict(r, merged=True) for r in gh_json(
        ["search", "prs", f"--owner={owner}", f"merged:>={cutoff}",
         "--limit", "40", "--json", velden])]
    cards = []
    for r in rows:
        if r["repository"]["name"] in ignore:
            continue
        pr = {"merged": r.get("merged", False), "draft": r.get("isDraft")}
        ts = time.mktime(time.strptime(r["updatedAt"][:19], "%Y-%m-%dT%H:%M:%S"))
        cards.append({"id": f"pr:{r['repository']['name']}:{r['number']}",
                      "repo": r["repository"]["name"],
                      "title": f"#{r['number']} {r['title']}",
                      "column": pr_column(pr), "age_days": age_days(ts, now),
                      "who": (r.get("author") or {}).get("login", ""),
                      "url": r.get("url", ""), "source": ""})
    return cards


def session_cards(runs_dir, now):
    """Een werksessie draait nog zolang er geen `result`-regel in het runbestand
    staat. Klaar is klaar: die verdwijnt van het bord, hij staat in het kanaal."""
    cards = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.jsonl"))):
        try:
            inhoud = open(path, errors="ignore").read()
            ts = os.path.getmtime(path)
        except OSError:
            continue
        if '"type":"result"' in inhoud.replace(" ", ""):
            continue
        naam = os.path.basename(path).rsplit("-", 1)[0]
        typ, _, wie = naam.partition("-")
        cards.append({"id": "session:" + os.path.basename(path),
                      "repo": "werksessie", "title": f"{typ} · {wie}",
                      "column": "building", "age_days": age_days(ts, now),
                      "who": wie, "url": "", "source": path})
    return cards


def build(cfg, now=None):
    """De momentopname. Een bron die faalt komt als `errors` mee — het bord moet
    kunnen zeggen 'ik weet het niet' in plaats van 'er is niets'."""
    now = now or time.time()
    src, cols = cfg["sources"], cfg["columns"]
    cards, errors = [], []
    cards += openspec_cards(src["openspec_glob"], now)
    try:
        cards += pr_cards(src["github_owner"], src.get("merged_days", 3), now,
                          set(src.get("ignore_repos") or ()))
    except Exception as e:
        errors.append(f"PR's niet opgehaald: {e}")
    try:
        cards += session_cards(src["session_runs"], now)
    except Exception as e:
        errors.append(f"werksessies niet gelezen: {e}")
    for c in cards:
        c["stale"] = is_stale(c, cols)
    cards.sort(key=lambda c: (-c["stale"], -c["age_days"]))
    return {"generated_at": now, "columns": summarise(cards, cols),
            "cards": cards, "errors": errors}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="doelbestand (atomisch geschreven)")
    ap.add_argument("--config")
    a = ap.parse_args()
    data = build(load_config(a.config))
    tekst = json.dumps(data, indent=1)
    if not a.out:
        print(tekst)
        return
    tmp = a.out + ".tmp"          # atomisch: nooit een half bestand serveren
    with open(tmp, "w") as f:
        f.write(tekst)
    os.replace(tmp, a.out)
    print(f"[board] {len(data['cards'])} kaarten -> {a.out}"
          + (f" ({len(data['errors'])} leesfout(en))" if data["errors"] else ""))


if __name__ == "__main__":
    main()
