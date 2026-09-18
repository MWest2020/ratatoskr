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
    args = [BUZZ, "messages", "send", "--channel", cid, "--content", "-"]
    if npub:
        args += ["--mention", npub]
    try:
        r = subprocess.run(args, env=env, input=line, capture_output=True,
                           text=True, timeout=25)
        if r.returncode != 0:
            print(f"[job {name}] statistiekregel mislukt (rc={r.returncode}): "
                  f"{r.stderr.strip()[:120]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"[job {name}] statistiekregel: relay-time-out", flush=True)


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

    prompt = job["prompt"]
    if context:
        prompt += f"\n\nContext:\n{context}"
    try:
        r = subprocess.run([CLAUDE, "-p", "--output-format", "json",
                            "--append-system-prompt", SYSTEM, prompt],
                           capture_output=True, text=True, timeout=MAX_S)
    except subprocess.TimeoutExpired:
        print(f"[job {name}] claude -p time-out — niets gepost", flush=True)
        return
    answer, stats = antwoord_en_kosten(r.stdout)
    if not answer:
        print(f"[job {name}] leeg antwoord — niets gepost", flush=True)
        return

    env = dict(os.environ)
    env["BUZZ_PRIVATE_KEY"] = nsec
    env["BUZZ_RELAY_URL"] = RELAY
    # own npub as --mention so arbitrary @words do not cause a post error
    ids = yaml.safe_load(open(os.path.join(os.path.dirname(HERE),
                                           "identities.yml")))["identities"]
    npub = ids.get(job["identity"], {}).get("npub", "")
    args = [BUZZ, "messages", "send", "--channel", job["channel"], "--content", "-"]
    if npub:
        args += ["--mention", npub]
    # Do check the send result: a slow or refusing relay must neither crash nor
    # falsely report "posted".
    try:
        sr = subprocess.run(args, env=env, input=answer, capture_output=True,
                            text=True, timeout=25)
    except subprocess.TimeoutExpired:
        print(f"[job {name}] relay-time-out bij posten — mogelijk niet gepost", flush=True)
        return
    if sr.returncode != 0:
        print(f"[job {name}] posten mislukt (rc={sr.returncode}): {sr.stderr.strip()[:160]}", flush=True)
        return
    print(f"[job {name}] gepost in kanaal {job['channel']}", flush=True)
    post_statistieken(name, job, stats, env, npub)


if __name__ == "__main__":
    main()
