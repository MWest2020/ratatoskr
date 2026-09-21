#!/usr/bin/env python3
"""Run one recurring job: fetch context → claude -p → post to the channel.

Config: jobs/jobs.yml. The private key of the posting identity comes through env
NSEC_<IDENTITY> (run-jobs.sh exports it from SOPS). Call it as:
    python3 jobs/run-job.py <jobname>
"""
import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RELAY = os.environ["BUZZ_RELAY_URL"]
MAX_S = 200
SYSTEM = ("Je bent een boomhuis-agent die een korte, eerlijke digest post in een "
          "kanaal. Geen hype, geen lange inleiding. Nederlands.")


def antwoord_en_kosten(stdout):
    """(answer, stats-dict) from `claude -p --output-format json`.

    Falls back on the raw text when that is not JSON. A changed output format of
    the CLI may cost the stats line, never the digest itself — the job is there
    for the digest."""
    try:
        d = json.loads(stdout)
    except (ValueError, TypeError):
        return (stdout or "").strip(), None
    if not isinstance(d, dict):
        return (stdout or "").strip(), None
    # The model is not a top-level field: `modelUsage` is keyed by model name
    # (measured 2026-09-18 against the installed CLI). One job = one model.
    return (d.get("result") or "").strip(), {
        "model": next(iter(d.get("modelUsage") or {}), "?"),
        "turns": int(d.get("num_turns") or 0),
        "cost": float(d.get("total_cost_usd") or 0.0),
    }


def post_statistieken(name, job, stats, env, npub):
    """One line per job run in #statistics — same shape as a chat-agent turn
    (agents/reporting.py). Without this the recurring jobs were the only part of
    the fleet that ran daily and cost money without ever showing up there, which
    made the channel look as if it reported at random."""
    if not stats:
        return
    cid = yaml.safe_load(open(os.path.join(ROOT, "channels.yml")))\
        ["channels"].get("statistics", {}).get("id")
    if not cid:
        return
    line = (f"{job['identity']} · job {name} · {stats['model']} · "
            f"{stats['turns']} turns · ${stats['cost']:.2f}")
    stuur([BUZZ, "messages", "send", "--channel", cid, "--content", "-"],
          env, line, npub, "statistiekregel", name)


def stuur(args, env, tekst, npub, wat, name):
    """Post `tekst`; True als het gelukt is. Een relay die traag is of weigert
    mag niet crashen en mag ook niet als "geplaatst" doorgaan."""
    args = list(args) + (["--mention", npub] if npub else [])
    try:
        r = subprocess.run(args, env=env, input=tekst, capture_output=True,
                           text=True, timeout=25)
    except subprocess.TimeoutExpired:
        print(f"[job {name}] {wat}: relay-time-out", flush=True)
        return False
    if r.returncode != 0:
        print(f"[job {name}] {wat} mislukt (rc={r.returncode}): "
              f"{r.stderr.strip()[:160]}", flush=True)
        return False
    return True


def meld_storing(name, job, reden, env, npub):
    """Een job die niets oplevert, zegt dát in zijn eigen kanaal.

    Op 2026-09-21 sneuvelden alle vier de terugkerende jobs om 08:00 op een
    kapotte claude-installatie. In het kanaal stond niets, en de storing kwam
    aan het licht doordat Mark om 15:30 vroeg "no standup this morning?".
    Afwezigheid leest als "niets te melden", en dat is precies het verkeerde
    antwoord op een kapotte pijplijn. Dezelfde regel als voor werksessies:
    een stille job bestaat niet.
    """
    tekst = f"⚠️ job {name} kon niet draaien: {reden}"
    print(f"[job {name}] storing gemeld: {reden}", flush=True)
    return stuur([BUZZ, "messages", "send", "--channel", job["channel"],
                  "--content", "-"], env, tekst, npub, "storingsmelding", name)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("gebruik: run-job.py <jobnaam>")
    name = sys.argv[1]
    jobs = yaml.safe_load(open(os.path.join(HERE, "jobs.yml")))["jobs"]
    if name not in jobs:
        raise SystemExit(f"onbekende job: {name}")
    job = jobs[name]
    nsec = os.environ.get("NSEC_" + job["identity"].upper(), "")
    if not nsec:
        raise SystemExit(f"geen NSEC_{job['identity'].upper()} in env")

    context = ""
    if job.get("context_cmd"):
        try:
            p = subprocess.run(["bash", "-c", job["context_cmd"]],
                               capture_output=True, text=True, timeout=60)
            context = (p.stdout or "").strip()[:6000]
        except subprocess.TimeoutExpired:
            # A slow context (relay/gh) must not crash the job. But it must not
            # silently pass as "nothing" either: give an explicit READ ERROR as
            # context, so a failure never reads as "no blockers / nothing done".
            context = ("(LEESFOUT: context-time-out — signaal onvolledig; "
                       "lees dit NIET als 'geen blokkades' of 'niks gebeurd')")
            print(f"[job {name}] context_cmd time-out — LEESFOUT-context", flush=True)

    # Eerst de verzendweg, dan pas het werk: zonder dit kon een storing in de
    # claude-aanroep niet gemeld worden, want de sleutel werd er pas ná
    # opgehaald.
    env = dict(os.environ)
    env["BUZZ_PRIVATE_KEY"] = nsec
    env["BUZZ_RELAY_URL"] = RELAY
    # own npub as --mention so arbitrary @words do not cause a post error
    ids = yaml.safe_load(open(os.path.join(os.path.dirname(HERE),
                                           "identities.yml")))["identities"]
    npub = ids.get(job["identity"], {}).get("npub", "")

    prompt = job["prompt"]
    if context:
        prompt += f"\n\nContext:\n{context}"
    try:
        r = subprocess.run([CLAUDE, "-p", "--output-format", "json",
                            "--append-system-prompt", SYSTEM, prompt],
                           capture_output=True, text=True, timeout=MAX_S)
    except subprocess.TimeoutExpired:
        return meld_storing(name, job, f"claude -p gaf na {MAX_S}s geen antwoord",
                            env, npub)
    except OSError as exc:
        # Precies het geval van 2026-09-21: het binaire bestand stond er wel,
        # maar was niet uitvoerbaar. Een OSError hier sloopte de hele job.
        return meld_storing(name, job, f"claude niet te starten ({exc.__class__.__name__}: "
                            f"{str(exc)[:120]})", env, npub)
    answer, stats = antwoord_en_kosten(r.stdout)
    if not answer:
        reden = (f"claude -p eindigde met rc={r.returncode}" if r.returncode
                 else "claude -p gaf een leeg antwoord")
        fout = (r.stderr or "").strip()[:160]
        return meld_storing(name, job, f"{reden}{': ' + fout if fout else ''}",
                            env, npub)

    if not stuur([BUZZ, "messages", "send", "--channel", job["channel"],
                  "--content", "-"], env, answer, npub, "posten", name):
        return
    print(f"[job {name}] gepost in kanaal {job['channel']}", flush=True)
    post_statistieken(name, job, stats, env, npub)


if __name__ == "__main__":
    main()
