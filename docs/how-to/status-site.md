---
status: current
last_reviewed: 2026-11-17
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

- **the page**, `data/status.json` (`"schema": 2`) in a westerweel-work
  worktree. Since 2026-11-17 (Mark: the page "exposes too much") per project
  only: the name, a link when the repository is public, progress
  (`done`/`total` of the current phase's `done_means`), the phase number, and
  per language (`en`, `nl`) a one-line `goal`, the current `phase`, two to four
  plain `next` lines, or a `note` when there are none. Read from the project's
  own `docs/reference/roadmap.yml` (`status_roadmap.py`) and shaped by
  `status_public.py`. No phase strip, no evidence links, no changes in flight:
  change names and issue numbers are coordination, not progress;
- **the digest**, `~/.local/state/ratatoskr/mark-digest.json`, never on the
  page, built from the build state and the open `propose:` and `build:` issues
  of every listed project, private ones included (`status_digest.py`): the open `waiting-on-mark` questions with their
  `Default:`, and the impediments: a build whose last verdict is a FAIL that has
  not moved for 12 hours, a build refusal of the last 24 hours (the breaker's
  "split it" among them), and a question open for more than three days. The
  coding session mails it to Mark once a day.

The projects are the keys of `orchestrator/status_site.yml`, plus any
repository the factory built for in the last week (`test_status_site_repos.py`).
Whether a project reaches the page is decided there too
(`status_public.shown`, `test_status_public.py`):

- `private: true`: never on the page (convergence, the crypto game; Mark
  2026-11-17). Its questions and impediments still reach the digest.
- a private GitHub repository, or one whose visibility cannot be read, is left
  out unless it has `show_private: true`; then it is named, not linked. jarvis
  is private and stays off (`show_private: false`) until Mark says otherwise.
- `show_client_names` (default `false`): each name under `clients` is replaced
  by a neutral description in the page's language ("Gooise Meren" becomes "a
  Dutch municipality" / "een gemeente").

A project shows only once it has a roadmap that parses.

Hugo renders the page with the site's `now` layout; Cloudflare Pages deploys on
every push to `main`.

## A roadmap, as data

Each project keeps `docs/reference/roadmap.yml`: `project`, `goal`, `current`
(a phase id), `phases` (`id`, `name`, `summary`) and `done_means` for the
current phase, each item with `status: done|open` and an `evidence` link (a PR,
issue or doc). An item is done only with evidence. Two optional keys are
for the public page only:

- `next`: two to four plain lines of what comes next. Without it the page takes
  the headlines of the open items (see below).
- `nl`: `goal`, `phase` and `next` in Dutch. The generator translates nothing
  and calls no translation service; without `nl` the NL page shows a Dutch
  template instead of English text: no goal, the phase as its number ("fase 2
  van 4", from `phase_index` and `phase_count`), and the note "5 open punten in
  deze fase; de omschrijving volgt." A roadmap that does not parse
(an unknown current phase, an item without a link) is left out rather than
shown wrong. The first versions were drafted from each repository's own docs on
2026-10-30 and await Mark's review.

## What never reaches the page

`orchestrator/status_strip.py` makes every goal, phase and next line plain
(`test_status_public.py` pins it on the real items of 2026-11-17):

- a parenthesis that holds a coordination marker goes as a whole: an issue or
  PR number (`#12`, `homelab#58`, `owner/repo#12`), "waits on", "Mark decided",
  "approved by Mark", a date, `default:`, "proposed", `ADR-0008`, `D36`,
  "decision 0005", "task 6.1", a link;
- a next line is the item's headline: the text before the first `;` or `:`,
  or the first two parts when the first is a label of at most two words;
- leftover references are removed; a line that still holds a marker is
  dropped, and a row that would still hold one is left out entirely.

Then `orchestrator/status_scrub.py` runs over every string, and its tests say so:

- **a secret stops the page.** Anthropic, Tailscale, GitHub and Cloudflare
  tokens, private keys, `password:`-style lines: nothing is written at all;
- e-mail addresses and UUIDs (channel ids, document ids) are replaced;
- wordsworth appears with change names and PR titles only, never document
  names or content;
- a private repository allowed with `show_private` is named but never linked;
  the waiting-on-Mark list never reaches the page (it leaked one issue link on
  the first publish, 2026-10-28).

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
