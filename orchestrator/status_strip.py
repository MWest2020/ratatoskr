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
3. references go (`REFS`): `#12`, `repo#12`, `owner/repo#12`, `GH-12`, `PR 12`,
   `issue 12`, `issues/12`, `ADR-0008`, `D36`, `D-36`, `decision 0005`, links,
   bare domains and paths;
4. what still holds a marker is dropped: better no line than a leaking one.

Markers (`COORD`), English and Dutch: the name Mark at all (the page is written
in the first person, so "Mark" there is always coordination), every reference
form above, a date (`2026-11-14`, `2026-11`, `17-11-2026`, `17/11/2026`,
`12 Nov`, `Nov 12`, `12 november`), "waits on/for", "wacht op", "besloot",
"besloten", "goedgekeurd", "default:", "standaard:", "proposal", "proposed",
"voorstel", "task 6.1", "gate 1.1", "change some-change-name".

`status_scrub` still runs afterwards (secrets stop the page; e-mail and ids go).
"""
import re

MONTH = (r"(jan(uary|uari)?|feb(ruary|ruari)?|mar(ch)?|maart|mrt|apr(il)?|may|mei|jun[ei]?|jul[iy]?"
         r"|aug(ust|ustus)?|sept?(ember)?|oct(ober)?|okt(ober)?|nov(ember)?|dec(ember)?)\b\.?")
TLD = r"(com|nl|org|net|io|dev|eu|app|ai|work|be|de)"
REF = (r"https?://\S+|\bwww\.\S+|\b[\w-]+(\.[\w-]+)*\.%s(/\S*)?(?![\w.])"
       r"|\b[\w.-]+/[\w.-]+/[\w./-]*|\b[\w-]+\.(md|ya?ml|py|json|sh|js|html)\b"
       r"|\b[\w.-]+/[\w.-]+#\d+|\b[\w.-]+#\d+|#\d+(/#?\d+)*"
       r"|\b(GH|PRs?|issues?|pulls?)[-/ #]?\d+|\bADR[- ]?\d+|\bD-?\d{1,3}\b|\bdecisions? \d+") % TLD
DATE = (r"\b\d{4}-\d\d(-\d\d)?\b|\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b"
        r"|\b\d{1,2} %s|\b%s \d{1,2}\b" % (MONTH, MONTH))
COORD = re.compile(
    r"(?i)" + REF + "|" + DATE +
    r"|\bMark\b|\bPRs?\b|\bwait(s|ing)? (on|for)\b|\bwacht(en|t)? op\b|\bbesl(oot|oten)\b|\bgoedgekeurd\b"
    r"|\b(default|standaard):|\bpropos(al|ed)\b|\bvoorstel\b|\btasks? \d|\btaak \d|\bgate \d"
    r"|\bchange [a-z0-9]+(-[a-z0-9]+)+")
REFS = re.compile(r"(?i)" + REF)
INNER = re.compile(r"\([^()]*\)")
LEAD = {"en": r"(?:the\s+)?(?:municipality|city|town)\s+of\s+", "nl": r"(?:de\s+)?gemeente\s+"}


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


def _spelled(name):
    """A name matched with any spacing or hyphens between its words, or none."""
    return r"[\s-]*".join(re.escape(w) for w in name.split())


def client_pattern(client):
    """One client's names and aliases, with a leading "gemeente" or
    "municipality of" in either language, as one regex."""
    names = [client["name"], *client.get("aliases", [])]
    alts = "|".join(_spelled(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?i)(?:{LEAD['en']}|{LEAD['nl']})?\b(?:{alts})\b")


def mask_clients(text, clients, lang, show):
    """Client names replaced by a neutral description, unless `show`."""
    if text is None or show:
        return text
    for c in clients:
        alias = c.get(lang) or c.get("en") or ""
        text = client_pattern(c).sub(lambda m: alias[:1].upper() + alias[1:] if m.start() == 0 else alias, text)
    return text


def names_pattern(names):
    """Any of `names` as a whole word (the projects the page leaves out)."""
    names = [n for n in names if n]
    return re.compile(r"(?i)\b(" + "|".join(_spelled(n) for n in names) + r")\b") if names else None
