#!/usr/bin/env python3
"""Draai één recurring job: context ophalen → claude -p → post naar het kanaal.

Config: jobs/jobs.yml. Privésleutel van de post-identiteit komt via env
NSEC_<IDENTITY> (run-jobs.sh exporteert die uit SOPS). Aanroep:
    python3 jobs/run-job.py <jobnaam>
"""
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RELAY = os.environ["BUZZ_RELAY_URL"]
MAX_S = 200
SYSTEM = ("Je bent een boomhuis-agent die een korte, eerlijke digest post in een "
          "kanaal. Geen hype, geen lange inleiding. Nederlands.")


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
            # Een trage context (relay/gh) mag de job niet laten crashen. Maar ook
            # niet stil als "niks" doorgaan: geef een expliciete LEESFOUT als context,
            # zodat een storing nooit als "geen blokkades / niks gedaan" leest.
            context = ("(LEESFOUT: context-time-out — signaal onvolledig; "
                       "lees dit NIET als 'geen blokkades' of 'niks gebeurd')")
            print(f"[job {name}] context_cmd time-out — LEESFOUT-context", flush=True)

    prompt = job["prompt"]
    if context:
        prompt += f"\n\nContext:\n{context}"
    try:
        r = subprocess.run([CLAUDE, "-p", "--append-system-prompt", SYSTEM, prompt],
                           capture_output=True, text=True, timeout=MAX_S)
    except subprocess.TimeoutExpired:
        print(f"[job {name}] claude -p time-out — niets gepost", flush=True)
        return
    answer = (r.stdout or "").strip()
    if not answer:
        print(f"[job {name}] leeg antwoord — niets gepost", flush=True)
        return

    env = dict(os.environ)
    env["BUZZ_PRIVATE_KEY"] = nsec
    env["BUZZ_RELAY_URL"] = RELAY
    # eigen npub als --mention zodat willekeurige @woorden geen post-fout geven
    ids = yaml.safe_load(open(os.path.join(os.path.dirname(HERE),
                                           "identities.yml")))["identities"]
    npub = ids.get(job["identity"], {}).get("npub", "")
    args = [BUZZ, "messages", "send", "--channel", job["channel"], "--content", "-"]
    if npub:
        args += ["--mention", npub]
    # send-resultaat wél checken: een trage/weigerende relay mag niet crashen én niet
    # vals "gepost" melden.
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


if __name__ == "__main__":
    main()
