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
        p = subprocess.run(["bash", "-c", job["context_cmd"]],
                           capture_output=True, text=True, timeout=60)
        context = (p.stdout or "").strip()[:6000]

    prompt = job["prompt"]
    if context:
        prompt += f"\n\nContext:\n{context}"
    r = subprocess.run([CLAUDE, "-p", "--append-system-prompt", SYSTEM, prompt],
                       capture_output=True, text=True, timeout=MAX_S)
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
    subprocess.run(args, env=env, input=answer, capture_output=True,
                   text=True, timeout=25)
    print(f"[job {name}] gepost in kanaal {job['channel']}", flush=True)


if __name__ == "__main__":
    main()
