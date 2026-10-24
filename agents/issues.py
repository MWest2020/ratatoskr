# SPDX-License-Identifier: MIT
"""The shared room's trail on GitHub: create, comment, relabel, close.

The listener writes here, never the model: every call is one fixed `gh` argv
list built from validated parts, as in readshell.py. A failure returns a reason
instead of raising, so the room can SAY that the trail broke; a turn that is
not on its issue must never look like one that is.
"""
import json
import re
import subprocess

import board

OWNER = "MWest2020"
TIMEOUT_S = 30
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
BASE_LABELS = ("agent-work",)
COLOR = "5319e7"


def _repo(repo):
    if not NAME.match(repo or "") or ".." in repo:
        raise ValueError(f"not a repository name: {repo!r}")
    return f"{OWNER}/{repo}"


def _gh(argv, runner, body=None):
    """(stdout, error); error is "" on success. A body goes on stdin: it is free
    text from a model and a human, and as an argv element it would be one
    quoting mistake away from a flag."""
    kw = {"input": body} if body is not None else {}
    try:
        p = runner(argv, capture_output=True, text=True, timeout=TIMEOUT_S, **kw)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"gh did not finish: {e}"
    if p.returncode != 0:
        return "", (p.stderr.strip().splitlines() or ["gh failed, no reason given"])[0]
    return p.stdout, ""


def labels(room, handle):
    return [*BASE_LABELS, f"room:{room}", f"agent:{handle}"]


def ensure_labels(repo, names, runner=subprocess.run):
    """Create the labels if they are missing. `--force` makes it idempotent."""
    for n in names:
        _, err = _gh(["gh", "label", "create", n, f"--repo={_repo(repo)}",
                      f"--color={COLOR}", "--force"], runner)
        if err:
            return err
    return ""


def create(repo, title, body, label_names, runner=subprocess.run):
    """(number, url, error)."""
    err = ensure_labels(repo, label_names, runner)
    if err:
        return 0, "", err
    argv = ["gh", "issue", "create", f"--repo={_repo(repo)}", f"--title={title[:120]}",
            "--body-file=-"] + [f"--label={n}" for n in label_names]
    out, err = _gh(argv, runner, body)
    m = re.search(r"/issues/(\d+)\s*$", out.strip())
    if err or not m:
        return 0, "", err or f"no issue url in gh output: {out.strip()[:80]!r}"
    board.note(repo, int(m.group(1)), body, title=title)   # the card follows the issue
    return int(m.group(1)), out.strip(), ""


def comment(repo, number, body, runner=subprocess.run):
    argv = ["gh", "issue", "comment", str(int(number)), f"--repo={_repo(repo)}",
            "--body-file=-"]
    err = _gh(argv, runner, body)[1]
    if not err:
        board.note(repo, number, body)
    return err


def relabel(repo, number, old, new, runner=subprocess.run):
    err = ensure_labels(repo, [new], runner)
    if err:
        return err
    argv = ["gh", "issue", "edit", str(int(number)), f"--repo={_repo(repo)}",
            f"--add-label={new}", f"--remove-label={old}"]
    return _gh(argv, runner)[1]


def close(repo, number, body, runner=subprocess.run):
    argv = ["gh", "issue", "close", str(int(number)), f"--repo={_repo(repo)}",
            "--reason=completed", f"--comment={body[:4000]}"]
    return _gh(argv, runner)[1]


def url(repo, number):
    return f"https://github.com/{_repo(repo)}/issues/{int(number)}"


def open_titled(repo, title, runner=subprocess.run):
    """Numbers of the open issues whose title is exactly `title`."""
    out, err = _gh(["gh", "issue", "list", f"--repo={_repo(repo)}", "--state=open",
                    "--limit=50", f"--search={title} in:title", "--json=number,title"], runner)
    if err:
        return []
    try:
        return [r["number"] for r in json.loads(out or "[]") if r.get("title") == title]
    except ValueError:
        return []
