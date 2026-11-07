# SPDX-License-Identifier: MIT
"""The `!newrepo` marker: odin (or Mark) has the listener create a repository.

Mark, 2026-11-07: "odin moet dat wel kunnen" (the bubbels2 experiment stalled
because the factory could not create its own repository). The listener checks
and acts, not the model:

- the name is plain, not `alma`, and holds no `conduction`;
- the repository does not exist yet;
- at most `new_repos_per_day` (factory.yml) a calendar day.

It is always created PRIVATE; making one public stays Mark's decision. The
bootstrap from `templates/newrepo/` is pushed over SSH, because the gh OAuth
token has no `workflow` scope and the template carries CI. Only a successful
create is recorded in the state file, and only recorded names join `repos` and
`readable` (`merge_known`): an existing repository can never get in this way.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

import activity

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "templates", "newrepo")
STATE = os.path.expanduser("~/.local/state/ratatoskr/created_repos.json")
MARKER = re.compile(r"^!newrepo\s+([A-Za-z0-9][A-Za-z0-9._-]{1,99})\s+(\S.{0,200})$")
AUTHOR = ["-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com"]
# The labels the build and propose roads put on their issues (issues.create fails without them).
LABELS = ("agent-work", "propose", "build", "waiting-on-mark")


def read_marker(text, own=True):
    """(name, description) or None. `own`: only the first line counts."""
    lines = (text or "").strip().splitlines()
    for ln in (lines[:1] if own else lines):
        m = MARKER.match(ln.strip())
        if m:
            return m.group(1), m.group(2).strip()
    return None


def unread(text):
    """A note when the first line starts with `!newrepo` and does not parse."""
    first = ((text or "").strip().splitlines() or [""])[0].strip()
    if not first.startswith("!newrepo") or MARKER.match(first):
        return ""
    return ("⚠ `!newrepo` not understood, nothing created. The first line must be "
            "`!newrepo <name> <one-line description>`: letters, digits, `.`, `_`, `-`, "
            "2-100 characters, a description of at most 200.")


def load(path=STATE):
    try:
        return json.load(open(path)).get("repos") or []
    except (OSError, ValueError):
        return []


def record(entry, path=STATE):
    rows = load(path) + [entry]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"repos": rows}, fh, indent=1)
    os.replace(tmp, path)


def merge_known(cfg, path=STATE):
    """Add the repositories this listener created to `repos` and `readable`, in
    place, so every reader of those lists (builds, proposals, reads) sees them."""
    for row in load(path):
        for key in ("repos", "readable"):
            names = cfg.setdefault(key, [])
            if row["name"].lower() not in (n.lower() for n in names):
                names.append(row["name"])


def created_today(path=STATE, now=time.time):
    today = time.strftime("%Y-%m-%d", time.localtime(now()))
    return sum(1 for r in load(path)
               if time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0))) == today)


def exists(owner, name, runner=subprocess.run):
    """True, False, or None when GitHub could not be asked."""
    try:
        p = runner(["gh", "api", f"repos/{owner}/{name}", "--jq", ".full_name"],
                   capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode == 0:
        return True
    return False if "Not Found" in (p.stderr + p.stdout) else None


def check(cfg, name, path=STATE, runner=subprocess.run, now=time.time):
    """None when the repository may be created, else the reason it may not."""
    low = name.lower()
    if low == "alma" or "conduction" in low:
        return f"`{name}` is a name the factory never creates"
    cap = int(cfg.get("new_repos_per_day", 2))
    if created_today(path, now) >= cap:
        return f"today's limit of {cap} new repositories is used up"
    found = exists(cfg["owner"], name, runner)
    if found is None:
        return f"could not ask GitHub whether `{name}` exists; try again later"
    if found:
        return f"`{cfg['owner']}/{name}` exists already"
    return None


def render(dst, name, description, starter, today):
    clean = description.replace('"', "'").replace("\n", " ")
    values = {"{{NAME}}": name, "{{DESCRIPTION}}": clean, "{{STARTER}}": starter,
              "{{DATE}}": today, "{{YEAR}}": today[:4]}
    shutil.copytree(TEMPLATE, dst)
    for root, _, files in os.walk(dst):
        for f in files:
            p = os.path.join(root, f)
            text = open(p).read()
            for k, v in values.items():
                text = text.replace(k, v)
            with open(p, "w") as fh:
                fh.write(text)


def create(cfg, name, description, starter, runner=subprocess.run, now=time.time,
           path=STATE, home=os.path.expanduser("~")):
    """Create, bootstrap and record. Returns (url, error); error "" on success.
    A repository that was created but whose bootstrap failed is still recorded:
    it is ours, and the message says what is missing."""
    owner = cfg["owner"]

    def run(cmd, cwd=None):
        p = runner(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        return "" if p.returncode == 0 else (p.stderr or p.stdout).strip()[-300:]

    err = run(["gh", "repo", "create", f"{owner}/{name}", "--private",
               "--description", description[:200]])
    if err:
        return "", f"gh repo create failed: {err}"
    today = datetime.date.fromtimestamp(now()).isoformat()
    record({"name": name, "ts": int(now()), "by": starter, "description": description}, path)
    url = f"https://github.com/{owner}/{name}"
    work = tempfile.mkdtemp(prefix="newrepo-")
    try:
        repo = os.path.join(work, name)
        render(repo, name, description, starter, today)
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                    ["git", *AUTHOR, "commit", "-q", "-m",
                     f"Bootstrap {name} (Ratatoskr !newrepo, started by {starter})"],
                    ["git", "remote", "add", "origin", f"git@github.com:{owner}/{name}.git"],
                    ["git", "push", "-q", "-u", "origin", "main"]):
            err = run(cmd, cwd=repo)
            if err:
                return url, f"created, but the bootstrap stopped at `{' '.join(cmd[:3])}`: {err}"
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for label in LABELS:
        run(["gh", "label", "create", label, "--repo", f"{owner}/{name}", "--force"])
    # The propose road writes in a worktree of ~/<name> (propose_wiring.CLONES).
    if not os.path.exists(os.path.join(home, name)):
        err = run(["git", "clone", "-q", f"git@github.com:{owner}/{name}.git",
                   os.path.join(home, name)])
        if err:
            return url, f"created, but no local clone for proposals: {err}"
    return url, ""


def act(cfg, name, description, starter, runner=subprocess.run, now=time.time, path=STATE,
        home=os.path.expanduser("~")):
    """The whole road for one marker: check, create, join the lists, and the
    line for the channel. A refusal is always said, never silent."""
    why = check(cfg, name, path, runner, now)
    if why:
        return f"⛔ repo not created: {why}"
    url, err = create(cfg, name, description, starter, runner, now, path, home)
    if not url:
        return f"⛔ repo not created: {err}"
    merge_known(cfg, path)
    activity.record("newrepo", starter, name, ref="created")
    line = f"📦 repo created: {cfg['owner']}/{name} (private) · {url}"
    if err:
        return f"{line}\n⚠ {err}"
    return line + "; on the factory's list now, so `!propose` and `!build` work there"
