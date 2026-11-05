# SPDX-License-Identifier: MIT
"""After a build's PR merges: request the next step of its sequence, through
the same `!build` road as a chat command (openspec change
`chain-next-step-after-merge`). The factory sat idle twice in early November
2026 after a merge whose next step was ready, because nothing started it
until a person asked.

`setup` returns `chain(m)`, called from `propose_wiring.after_merge` for a
merged build (never for a `propose` or `archive` merge). Every outcome is
said in the channel the build came from, or logged when the entry has no
`cid` (an adopted entry across a restart).
"""
import json
import subprocess

import chain_next
import close_on_archive


def read_proposal(owner, repo, change, runner=subprocess.run):
    """(text, "") or ("", reason). The raw `Accept` header is required: without
    it GitHub serves JSON metadata, whose body starts with `{` — a failed
    read, never a change with no next step."""
    try:
        p = runner(["gh", "api", f"repos/{owner}/{repo}/contents/openspec/changes/"
                    f"{change}/proposal.md", "-H", "Accept: application/vnd.github.raw+json"],
                   capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"could not ask GitHub: {e}"
    if p.returncode != 0:
        return "", (p.stderr.strip().splitlines() or ["gh failed, no reason given"])[-1]
    if p.stdout.lstrip().startswith("{"):
        return "", "got JSON instead of the raw file"
    return p.stdout, ""


def merged(owner, repo, parent, just_merged, runner=subprocess.run):
    """True when `parent` is the change that just merged, or a PR titled
    exactly `build: <parent>` (the title `build_merge.open_pr` writes) is
    merged on this repository."""
    if parent == just_merged:
        return True
    try:
        p = runner(["gh", "pr", "list", f"--repo={owner}/{repo}", "--state=merged",
                    "--search", f"build: {parent} in:title", "--json=title"],
                   capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    if p.returncode != 0:
        return False
    try:
        rows = json.loads(p.stdout or "[]")
    except ValueError:
        return False
    return any(r.get("title") == f"build: {parent}" for r in rows)


def setup(cfg, hub, say, try_build, runner=subprocess.run, log=print):
    owner = cfg["owner"]

    def tell(m, text):
        cid = m.get("cid")
        if cid:
            say(cid, text)
        else:
            log(f"[listener] chain {m.get('repo')} {m.get('change')}: {text}", flush=True)

    def chain(m):
        repo, change = m.get("repo"), m.get("change")
        if not repo or not change:
            return
        text, err = read_proposal(owner, repo, change, runner)
        if err:
            return tell(m, f"⛔ chain: could not read `{change}`'s proposal: {err}")
        parsed = chain_next.parse(text)
        if parsed["malformed"]:
            return tell(m, f"⛔ chain: `{change}`'s `## Next` section names no change")
        nxt = parsed["next"]
        if not nxt:
            return tell(m, f"ℹ chain: `{change}` names no next step")
        by_archive, aerr = close_on_archive.archived(owner, repo, runner)
        if not aerr and by_archive.get(nxt):
            return tell(m, f"ℹ chain: `{nxt}` is already archived; not building it again")
        next_text, nerr = read_proposal(owner, repo, nxt, runner)
        if nerr:
            return tell(m, f"⛔ chain: could not read `{nxt}`'s proposal: {nerr}")
        next_parsed = chain_next.parse(next_text)
        missing = next((p for p in next_parsed["parents"]
                        if not merged(owner, repo, p, change, runner)), None)
        if missing:
            return tell(m, f"⏳ chain: `{nxt}` waits on `{missing}`, not merged yet")
        if next_parsed["precondition"]:
            return tell(m, f"ℹ chain: `{nxt}` has a deploy precondition; a person starts it")
        try_build(f"!build {repo} {nxt}", hub, m.get("cname", ""), m.get("cid"), own=True)

    return chain
