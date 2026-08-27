#!/usr/bin/env python3
"""Boomhuis chat-agent — dunne listener rond claude -p (sub-first).

Luistert de kanalen af via buzz-cli, en zodra een bericht de agent noemt
(@assistent), draait het claude -p met een beetje kanaalcontext en post het
antwoord terug als de agent-identiteit. Bewust simpel/saai en auditeerbaar:
geen daemon-magie, geen state buiten een 'gezien'-set en git.

Env:
  AGENT_NSEC        nsec van de agent (identiteit 'assistent')
  BUZZ_RELAY_URL    ws://192.168.178.60:3000
  AGENT_HANDLE      mention-trigger (default '@assistent')
  BUZZ_BIN          pad naar buzz-cli
  CLAUDE_BIN        pad naar claude
"""
import json
import os
import subprocess
import time

BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
HANDLE = os.environ.get("AGENT_HANDLE", "@assistent")
RELAY = os.environ["BUZZ_RELAY_URL"]
AGENT_NSEC = os.environ["AGENT_NSEC"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8         # hoeveel recente berichten als context
MAX_TURN_S = 120    # harde cap per claude-aanroep

CHANNELS = {
    "runs": "74504227-8f82-42d5-b943-e0bc059778bc",
    "escalatie": "c1a0db51-3c96-46f9-9afa-1f03acfd87a3",
    "bouw": "69cf0949-f1ab-4383-9627-8ef0f51977e1",
    "review": "b829eac4-a49b-4336-813e-90cdfa1a81c7",
    "architectuur": "1ed0e697-7187-43ae-b0a1-faa667e1c93e",
    "marketing": "b3b40816-ed50-4983-977b-44a3f8e9271f",
}
NAMES = {
    "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db": "mark",
    "27308f27bfdac7d051d6c79cbacffcf20eccc54abccb7495db68a58f25d083f0": "orchestrator",
    "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255": "assistent",
}
SELF_PUB = "378aaf0fca61133c14bbd0e6a4ab26cea4cdffdeb7d2513fdc458b1b9d864255"

SYSTEM = (
    "Je bent 'assistent', een chat-agent in Marks boomhuis (een self-hosted "
    "team-chat voor zijn agent-ecosysteem). Antwoord kort, concreet en in het "
    "Nederlands, als een behulpzame collega in een kanaal. Geen preek, geen "
    "lange inleidingen. Je praat mee in het kanaal; je hebt geen shell- of "
    "repo-toegang vanuit hier — als iets echt werk vergt, benoem het als "
    "vervolgstap, voer het niet zelf uit."
)


def buzz_env():
    e = dict(os.environ)
    e["BUZZ_PRIVATE_KEY"] = AGENT_NSEC
    e["BUZZ_RELAY_URL"] = RELAY
    return e


def get_messages(cid):
    p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                       env=buzz_env(), capture_output=True, text=True, timeout=25)
    if p.returncode != 0:
        return []
    try:
        d = json.loads(p.stdout)
    except Exception:
        return []
    msgs = d if isinstance(d, list) else d.get("messages", [])
    return sorted(msgs, key=lambda m: m.get("created_at", 0))


def send(cid, content):
    subprocess.run([BUZZ, "messages", "send", "--channel", cid, "--content", "-"],
                   env=buzz_env(), input=content, capture_output=True,
                   text=True, timeout=25)


def ask_claude(prompt):
    p = subprocess.run([CLAUDE, "-p", "--append-system-prompt", SYSTEM, prompt],
                       capture_output=True, text=True, timeout=MAX_TURN_S)
    out = (p.stdout or "").strip()
    return out or "(geen antwoord)"


def build_prompt(chan_name, recent, trigger_text):
    lines = [f"Kanaal #{chan_name}. Recente berichten:"]
    for m in recent:
        who = NAMES.get(m.get("pubkey", ""), "iemand")
        lines.append(f"{who}: {m.get('content','')}")
    lines.append("")
    lines.append(f"Je bent genoemd met '{HANDLE}'. Reageer op het laatste "
                 f"bericht van mark/gebruiker: {trigger_text!r}")
    return "\n".join(lines)


def main():
    seen = set()
    # bootstrap: markeer bestaande berichten als gezien (niet op oude reageren)
    for cid in CHANNELS.values():
        for m in get_messages(cid):
            seen.add(m.get("id"))
    print(f"[listener] actief; luistert op {HANDLE} in {len(CHANNELS)} kanalen",
          flush=True)
    while True:
        for name, cid in CHANNELS.items():
            msgs = get_messages(cid)
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                if m.get("pubkey") == SELF_PUB:
                    continue  # niet op jezelf reageren
                content = m.get("content", "")
                if HANDLE.lower() not in content.lower():
                    continue
                print(f"[listener] mention in #{name}: {content[:60]}", flush=True)
                recent = msgs[max(0, i - MAX_CTX):i + 1]
                try:
                    answer = ask_claude(build_prompt(name, recent, content))
                except subprocess.TimeoutExpired:
                    answer = "(time-out — vraag te zwaar voor een chatbeurt)"
                except Exception as e:
                    answer = f"(fout: {e})"
                send(cid, answer)
                print(f"[listener] geantwoord in #{name}", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
