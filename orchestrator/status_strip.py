# SPDX-License-Identifier: MIT
"""Plain language for the public overview: no internal coordination notes.

Mark, 2026-11-17, on westerweel.work/nu/: the page "exposes too much". A
roadmap item is written for the people working on it ("built (#449) and
deployed (homelab#58); the run is next", "waits on Mark: #13", "Mark decided
...", "ADR-0008"); the public page shows what is being worked on, not how it is
coordinated. Rules, in order:

1. a parenthesis that holds a coordination marker (`COORD`) goes as a whole;
2. for a list item, only the headline stays: the text before the first `;` or
   `:` (outside parentheses), or the first two parts when the first is a short
   label of at most two words ("Android app: a spoken round trip");
3. references go: `#12`, `repo#12`, `owner/repo#12`, `ADR-0008`, `D36`,
   `decision 0005`, links;
4. what still holds a marker is dropped: better no line than a leaking one.

`status_scrub` still runs afterwards (secrets stop the page; e-mail and ids go).
"""
import re

COORD = re.compile(
    r"(?i)#\d|\bADR[- ]?\d|\bD\d{1,3}\b|\bdecisions? \d|\bwait(s|ing)? on\b"
    r"|\bMark (decided|approved|funded|said|chose|asked)\b|\b(approved|decided) by Mark\b"
    r"|\bMark,? \d{4}-\d\d|\b\d{4}-\d\d-\d\d\b|\bdefault:|\bpropos(al|ed)\b|\bPRs?\b"
    r"|\btasks? \d|\bgate \d|https?://|\bchange [a-z0-9]+(-[a-z0-9]+)+")
REFS = re.compile(
    r"https?://\S+|\b[\w.-]+/[\w.-]+#\d+|\b[\w.-]+#\d+|#\d+(/#?\d+)*"
    r"|\bADR[- ]?\d+|\bD\d{1,3}\b|\bdecisions? \d+")
INNER = re.compile(r"\([^()]*\)")


def _drop_coord_parens(text):
    """Every innermost parenthesis with a marker goes, until none is left."""
    hide = lambda m: "" if COORD.search(m.group(0)) else "\0" + m.group(0)[1:-1] + "\1"  # noqa: E731
    while True:
        out = INNER.sub(hide, text)
        if out == text:
            return out.replace("\0", "(").replace("\1", ")")
        text = out


def _split_outside(text, sep):
    """`text` split on `sep`, ignoring separators inside parentheses."""
    parts, depth, cur, i = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and text.startswith(sep, i):
            parts.append(cur)
            cur, i = "", i + len(sep)
            continue
        cur, i = cur + ch, i + 1
    return parts + [cur]


def _tidy(text):
    text = REFS.sub("", text)
    text = re.sub(r"\(\s*[,;]?\s*\)", "", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,;:-")


def plain(text):
    """A goal or phase name without coordination notes, or None when that
    cannot be done cleanly."""
    if not text:
        return None
    out = _tidy(_drop_coord_parens(str(text)))
    return out if out and not COORD.search(out) else None


def headline(text):
    """A roadmap item as one plain 'next up' line, or None to drop it."""
    if not text:
        return None
    text = _drop_coord_parens(str(text))
    text = _split_outside(text, "; ")[0]
    parts = _split_outside(text, ": ")
    head = parts[0]
    if len(head.split()) <= 2 and len(parts) > 1:
        head = f"{head}: {parts[1]}"
    return plain(head)


def mask_clients(text, clients, lang, show):
    """Client names replaced by a neutral description, unless `show`."""
    if text is None or show:
        return text
    for c in clients:
        text = re.sub(rf"(?i)\b{re.escape(c['name'])}\b", c.get(lang) or c.get("en") or "", text)
    return text
