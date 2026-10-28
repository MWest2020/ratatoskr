---
status: current
last_reviewed: 2026-10-28
---

# The public overview on westerweel.work/nu/

Mark, 2026-10-28: a dedicated overview on his own site of what the factory is
working on; everything public, except sensitive information. It lives at
<https://westerweel.work/nu/> (NL) and <https://westerweel.work/en/now/> (EN).

## How it is built

`orchestrator/status_site.py` builds `data/status.json` from facts only:

- the build state (`~/.local/state/ratatoskr/builds/state.json`): proposing,
  queued, building, merging, deploying;
- per project, the open `propose:` issues (a change in flight) and their last
  role verdict (a FAIL means stuck until an amend);
- merged PRs of the last seven days, marked *deployed* when the homelab log
  carries the factory's `deploy <sha>` commit for them;
- `build refused` lines from the listener's journal of the last 24 hours;
- issues labelled `waiting-on-mark` in any MWest2020 repository: the title is
  the question, and a line `Default: …` in the body says what happens if Mark
  does not answer.

Hugo renders the file with the site's `now` layout; Cloudflare Pages deploys on
every push to `main`.

## What never reaches the page

`orchestrator/status_scrub.py` runs over every string, and its tests say so:

- **a secret stops the page.** Anthropic, Tailscale, GitHub and Cloudflare
  tokens, private keys, `password:`-style lines: nothing is written at all;
- e-mail addresses and UUIDs (channel ids, document ids) are replaced;
- wordsworth appears with change names and PR titles only, never document
  names or content;
- a private repository (convergence) is named with its changes, stages and
  questions, but never linked; that holds for the waiting-on-Mark list too
  (it leaked one issue link on the first publish, 2026-10-28).

## When it runs

A systemd user timer (`ratatoskr-status-site.timer`) every two hours. The
script pushes only when the content changed (the generation time aside) and at
most once every two hours: **Cloudflare Pages' free tier has a monthly build
budget**, and every push is a build.

```bash
# install (once), from the listener's tree
cp orchestrator/systemd/ratatoskr-status-site.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ratatoskr-status-site.timer

# look without publishing
python3 orchestrator/status_site.py --print
```

The site checkout is a dedicated worktree, `~/.worktrees/westerweel-status`,
reset to `origin/main` on every run; nothing else may work in it.

## Asking Mark something

Open an issue in the repository it is about, label it `waiting-on-mark`, put
the question in the title, a link in the body and a line `Default: …`. Then
mail it to him (the agreement in his memory: points for Mark go by mail, with
a link). It shows on the page at the next run.
