#!/usr/bin/env python3
"""What may reach the public overview on westerweel.work/nu/, enforced in code.

Mark, 2026-10-28: "alles mag publiek — enkel niet als het gevoelige info heeft".
The overview is built from facts (state files, GitHub), and every string passes
through `clean()` before it is written. Two kinds of rule:

- **Refuse:** a secret anywhere means nothing is written at all (`Leak`). A
  token that slipped into an issue title must stop the page, not be published
  with a blacked-out middle.
- **Strip:** identifiers that are not secret but are not for a public page
  either: email addresses, UUIDs (channel ids, document ids), so a wordsworth
  document can never be pointed at from here.
"""
import re

SECRETS = [
    re.compile(p) for p in (
        r"sk-ant-[A-Za-z0-9_-]{8,}",            # Anthropic
        r"tskey-[A-Za-z0-9_-]{8,}",             # Tailscale
        r"\bgh[pousr]_[A-Za-z0-9]{20,}",        # GitHub tokens
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"\bcfat_[A-Za-z0-9]{20,}",             # Cloudflare account tokens
        r"\bnsec1[0-9a-z]{20,}",                # nostr secret keys
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)\b(password|passwd|wachtwoord|api[_-]?key|secret)\s*[:=]\s*\S+",
        r"\bAKIA[0-9A-Z]{16}\b",                # AWS access key ids
    )
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


class Leak(Exception):
    """A secret was found in what would be published; nothing is written."""


def clean(text):
    """One string as it may appear publicly, or Leak."""
    if text is None:
        return None
    s = str(text)
    for pat in SECRETS:
        if pat.search(s):
            raise Leak(f"secret-like pattern {pat.pattern[:24]!r} in output")
    s = EMAIL.sub("[e-mail]", s)
    s = UUID.sub("[id]", s)
    return s.strip()


def clean_tree(obj):
    """Every string in a JSON-able tree through `clean`; keys are ours."""
    if isinstance(obj, dict):
        return {k: clean_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_tree(v) for v in obj]
    if isinstance(obj, str):
        return clean(obj)
    return obj


def public_url(url, repo_public):
    """Links only into public repositories; a private one is named, not linked."""
    return url if repo_public else None
