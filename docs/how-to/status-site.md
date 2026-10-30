---
status: current
last_reviewed: 2026-10-28
---

# The public overview on westerweel.work/nu/

Mark, 2026-10-28: a dedicated overview on his own site; everything public,
except sensitive information. 2026-10-30: *"what I really want is the phase and
the roadmap, high-level, and what the gap is until it's done. Waiting on Mark I'd
rather have daily by mail; stuck is an impediment? then also in the mail."* It
lives at <https://westerweel.work/nu/> (NL) and <https://westerweel.work/en/now/>
(EN).

## How it is built

`orchestrator/status_site.py` builds two things from facts, on every run:

- **the page**, `data/status.json` in a westerweel-work worktree: per project
  its goal, the phase strip (past, current, next), progress toward done for the
  current phase, and the gap (the open items), read from the project's own
  `docs/reference/roadmap.yml` (`status_roadmap.py`), plus one compact line of
  the changes in flight (from the build state and open `propose:` issues);
- **the digest**, `~/.local/state/ratatoskr/mark-digest.json`, never on the
  page (`status_digest.py`): the open `waiting-on-mark` questions with their
  `Default:`, and the impediments: a build whose last verdict is a FAIL that has
  not moved for 12 hours, a build refusal of the last 24 hours (the breaker's
  "split it" among them), and a question open for more than three days. The
  coding session mails it to Mark once a day.

Hugo renders the page with the site's `now` layout; Cloudflare Pages deploys on
every push to `main`.

## A roadmap, as data

Each project keeps `docs/reference/roadmap.yml`: `project`, `goal`, `current`
(a phase id), `phases` (`id`, `name`, `summary`) and `done_means` for the
current phase, each item with `status: done|open` and an `evidence` link (a PR,
issue or doc). An item is done only with evidence. A roadmap that does not parse
(an unknown current phase, an item without a link) is left out rather than
shown wrong. The first versions were drafted from each repository's own docs on
2026-10-30 and await Mark's review.

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
the question in the title, a link in the body and a line `Default: …`, and keep
going with that default. It reaches Mark in the next daily digest mail, not on
the page.
