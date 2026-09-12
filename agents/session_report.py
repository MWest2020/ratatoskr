# SPDX-License-Identifier: EUPL-1.2
"""Wat een sessie aan het eind in het kanaal zet.

Apart van sessions.py omdat dat bestand over processen en bestanden gaat en dit
over tekst — en omdat beide anders over de 200 regels gaan.

Eén regel bepaalt alles hier: **een stille sessie bestaat niet.** Faalt hij, komt
hij leeg terug of wordt hij afgekapt, dan staat de reden in het kanaal. Anders
leest een storing als "er was niets te melden", en dat is de false-clear die we
overal in deze repo bewaken.

Engels in de code per ADR-0001; deze module is nieuw.
"""
import re

# Een PR-link uit de uitvoer vissen. Een schrijvende sessie eindigt in een
# voorstel, en dat voorstel is het enige wat een mens hoeft aan te klikken.
PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")


def pull_request(text):
    """De LAATSTE PR-link in de uitvoer, of "". De laatste, want een sessie kan
    er onderweg een noemen als voorbeeld; de laatste is degene die hij opende."""
    found = PR_URL.findall(text or "")
    return found[-1] if found else ""


def footer(session, elapsed, result):
    """De statistiekregel: hoe lang, wat het kostte, hoeveel beurten — en bij een
    schrijvende sessie welke branch, zodat je het werk terug kunt vinden ook als
    er geen PR uit kwam."""
    parts = [f"— sessie `{session['type']}` · {int(elapsed // 60)}m{int(elapsed % 60):02d}s",
             f"${float(result.get('total_cost_usd') or 0.0):.2f}",
             f"{int(result.get('num_turns') or 0)} beurten"]
    if session.get("branch"):
        parts.append(f"branch `{session['branch']}`")
    return " · ".join(parts)


def result_text(session, elapsed):
    """Altijd iets. Een sessie die stil niets oplevert leest als 'niets te
    melden', en dat is precies wat we niet willen."""
    result = session.get("res") or {}
    answer = (result.get("result") or "").strip()
    foot = footer(session, elapsed, result)

    if not answer:
        return (f"⚠️ sessie `{session['type']}` eindigde zonder antwoord "
                f"(exit {session['proc'].returncode}). Log: {session['path']}\n{foot}")
    if result.get("is_error"):
        answer = (f"⚠️ sessie liep vast ({result.get('subtype') or 'error'}):\n{answer}")

    pr = pull_request(answer)
    if session.get("writes"):
        # Een schrijvende sessie zonder PR is niet per se mislukt, maar het is
        # wél het eerste wat je wilt weten.
        answer += (f"\n\n🔀 {pr}" if pr
                   else f"\n\n⚠️ geen pull request in de uitvoer — werk staat in "
                        f"`{session.get('workdir', '?')}`")
    return f"{answer}\n\n{foot}"
