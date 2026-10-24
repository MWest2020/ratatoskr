# SPDX-License-Identifier: MIT
"""The read shell: seven read-only GitHub lookups a chat agent may run.

Mark, 2026-10-05, in #architectuur: "@odin hoe ver weg zijn we van jou en een
shell?". A chat agent gets this program as its ONLY Bash, through the rule
`RULE` in its handbook definition. Why one program instead of `gh`/`git`
prefixes (openspec change odin-read-shell, design.md): a prefix rule bounds the
command, not its arguments. `gh` runs with Mark's full-scope token from
~/.config/gh/hosts.yml, and `git log --output=<file>` writes. Here the owner is
fixed, every argument is validated, and each question is one fixed argv list
run without a shell.

    python3 agents/readshell.py prs wordsworth
"""
import argparse
import re
import subprocess
import sys

RULE = "Bash(python3 agents/readshell.py:*)"
OWNER = "MWest2020"
MAX_LINES = 40
TIMEOUT_S = 20
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,49}$")

COMMANDS = {
    "log": "log <repo> [n] — the last n commits on the default branch",
    "branches": "branches <repo> — the branch names",
    "changes": "changes <repo> — open OpenSpec changes (openspec/changes, not archive)",
    "prs": "prs <repo> [n] — open pull requests",
    "issues": "issues <repo> [label] — open issues, optionally with one label",
    "checks": "checks <repo> <pr> — the checks of one pull request",
    # 2026-10-24: a role's FAIL verdict is posted on the build issue, and odin
    # could not read it, so it held a build twice for a cause on the issue
    "comments": "comments <repo> <issue> [n] — the last n comments on an issue or PR",
}


def repo(name):
    if not NAME.match(name or "") or ".." in name:
        raise argparse.ArgumentTypeError(f"not a repository name: {name!r}")
    return f"{OWNER}/{name}"


def count(s):
    try:
        n = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {s!r}")
    if not 1 <= n <= MAX_LINES:
        raise argparse.ArgumentTypeError(f"between 1 and {MAX_LINES}: {n}")
    return n


def pr_number(s):
    if not s.isdigit() or not 0 < int(s) < 10**7:
        raise argparse.ArgumentTypeError(f"not a PR number: {s!r}")
    return int(s)


def label(s):
    if not LABEL.match(s):
        raise argparse.ArgumentTypeError(f"not a label: {s!r}")
    return s


def parser():
    p = argparse.ArgumentParser(prog="readshell", description="Read-only GitHub lookups.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in COMMANDS:
        s = sub.add_parser(name)
        s.add_argument("repo", type=repo)
        if name in ("log", "prs"):
            s.add_argument("n", type=count, nargs="?", default=15)
        if name == "issues":
            s.add_argument("label", type=label, nargs="?")
        if name in ("checks", "comments"):
            s.add_argument("pr", type=pr_number)
        if name == "comments":
            s.add_argument("n", type=count, nargs="?", default=4)
    return p


def argv(a):
    """The one gh command for a parsed request. Pure, so the tests pin it."""
    r = a.repo
    if a.cmd == "log":
        return ["gh", "api", f"repos/{r}/commits?per_page={a.n}", "--jq",
                r'.[] | "\(.sha[0:7]) \(.commit.author.date[0:10]) '
                r'\(.commit.message | split("\n")[0])"']
    if a.cmd == "branches":
        return ["gh", "api", f"repos/{r}/branches?per_page=100", "--jq", ".[].name"]
    if a.cmd == "changes":
        return ["gh", "api", f"repos/{r}/contents/openspec/changes", "--jq",
                '.[] | select(.type == "dir" and .name != "archive") | .name']
    if a.cmd == "prs":
        return ["gh", "pr", "list", f"--repo={r}", "--state=open", f"--limit={a.n}",
                "--json=number,headRefName,title", "--jq",
                r'.[] | "#\(.number) \(.headRefName) — \(.title)"']
    if a.cmd == "issues":
        cmd = ["gh", "issue", "list", f"--repo={r}", "--state=open", "--limit=30",
               "--json=number,title,labels", "--jq",
               r'.[] | "#\(.number) \(.title) [\([.labels[].name] | join(", "))]"']
        return cmd + ([f"--label={a.label}"] if a.label else [])
    if a.cmd == "comments":
        return ["gh", "issue", "view", str(a.pr), f"--repo={r}", "--json=comments", "--jq",
                f".comments[-{a.n}:][] | " r'"— \(.author.login) \(.createdAt[0:16]):\n\(.body)"']
    return ["gh", "pr", "checks", str(a.pr), f"--repo={r}"]


def capped(text, limit=MAX_LINES):
    lines = text.rstrip("\n").splitlines()
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"… {len(lines) - limit} more lines not shown"]


def run(a, runner=subprocess.run):
    """Print the answer; return the exit code. Empty output says so: an empty
    answer and a failed one must never look the same."""
    try:
        p = runner(argv(a), capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print(f"readshell: {a.cmd} timed out after {TIMEOUT_S}s")
        return 1
    except OSError as e:
        print(f"readshell: {a.cmd} could not start gh: {e}")
        return 1
    # `gh pr checks` exits 8 while checks are pending and 1 when one fails;
    # both still print the table, which is the answer.
    if p.stdout.strip():
        print("\n".join(capped(p.stdout)))
        return 0
    if p.returncode != 0:
        why = (p.stderr.strip().splitlines() or ["no reason given"])[0]
        print(f"readshell: {a.cmd} {a.repo} failed: {why}")
        return 1
    print(f"(none: {a.cmd} {a.repo} returned nothing)")
    return 0


def stray_bash(allow):
    """Bash entries in a chat facet other than the read shell. A chat turn
    gets no free shell; bootstrap refuses the agent when this is not empty."""
    return [t for t in allow or []
            if str(t).split("(", 1)[0].strip() == "Bash" and t != RULE]


def clause(cfg):
    """What the system prompt says about the read shell — only when the
    definition allows it, so the announcement cannot drift from the mandate."""
    if RULE not in ((cfg or {}).get("allow") or []):
        return ""
    lines = "\n".join(f"- `python3 agents/readshell.py {u}`" for u in COMMANDS.values())
    return ("\n\nYou have a READ SHELL for the state of the work on GitHub. It is "
            "your only Bash command; run it exactly in this form, one call per "
            "command, from your working directory:\n"
            f"{lines}\n"
            f"Repositories are {OWNER}'s; give the name only (e.g. `wordsworth`). "
            "Anything else in Bash — pipes, `;`, other programs — is refused. It "
            "reads and changes nothing. Use it before you say what the state is.")


def main(args=None):
    return run(parser().parse_args(args))


if __name__ == "__main__":
    sys.exit(main())
