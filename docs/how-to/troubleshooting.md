---
status: actief
last_reviewed: 2026-11-26
---

# Troubleshooting

## First question: is the device on the tailnet?

    ssh buzz-relay 'sudo tailscale status'

A phone that was six hours offline looked exactly like an app failure; the app
fixes underneath were real but could not reach the device. Next, turn on the
access log (`RATATOSKR_ACCESSLOG=1`, then `docker logs buzz-prod-chat-1`). No
request at all means the device does not reach the server, and searching in
the app is pointless.

## After every deploy: all three layers

`chat/e2e/after-deploy.sh` runs `api.sh` (no session), `connection.sh` (logged
in) and `smoke.js` (a real browser). Run all three. `api.sh` was 38/38 green for
half a day while the app stood still.

## Push notifications

The chain, and where to look:

```
browser: bell → Notification.requestPermission()
       → GET  /api/push/vapid        (chat/push.py, VAPID_PUBLIC from chat.env)
       → pushManager.subscribe()     (Chrome talks to FCM)
       → POST /api/push/subscribe    → push_subs.json in the chat volume
sending, from the agent host:
  uv run orchestrator/push-notify.py --title … --body …
       → ssh buzz-relay 'sudo -n /usr/local/bin/boomhuis-push-subs read'
       → pywebpush (VAPID JWT + aes128gcm, Urgency: high, TTL 3600) → FCM
```

Diagnosis always starts in the access log: no `/api/push/vapid` means the
browser permission; `vapid` but no `/api/push/subscribe` means
`pushManager.subscribe()` itself failed.

Three silent breaks, all found the hard way:

1. **A moved file.** Subscriptions moved to the named volume while the sender
   read the old path: "0 subscribers". The sender now reads a `PATHS` list,
   newest first.
2. **Ownership.** A prune helper running as root wrote a fresh 0600 file; the
   chat (uid 10001) could then neither read nor store subscriptions. The helper
   now keeps owner and mode.
3. **A revoked permission.** Uninstalling the installed PWA revokes the
   origin's notification permission in Chrome and leaves it *blocked*. A
   blocked permission cannot be restored from the app —
   `requestPermission()` returns `denied` without asking. The only way back:
   Chrome → Settings → Site settings → Notifications → the host → Allow.

Every layer failed silently, which is what made this expensive. Every
permission state now shows something (`push-states.js` tests it), and a failed
subscription names its error.

## No image

`ping.sh --image` ([send an image](send-an-image.md)) fails before anything
is uploaded, and says why:

- **Exit 9**, `[ping] an image needs a caption`: the caption (third argument)
  is missing.
- **Exit 10**, `image_prep: <reason>` followed by `[ping] image refused
  (image_prep.py)`: the helper refused the file, nothing was sent and no key
  was decrypted. The reasons:
  - `<w>x<h> exceeds 2560 px per side`: make it smaller at the source (no
    Playwright `fullPage`, viewport or clip at most 2560, `scale: "css"`;
    matplotlib `figsize × dpi` at most 2560);
  - `orientation <n>: rotate the pixels before sending`;
  - `animated PNG` or `animated WebP`;
  - `APP14 …`, `RGB-coded JPEG …` or `component count 4 …`: re-save as PNG;
  - `GIF/SVG/HEIC/AVIF/PDF is not a supported image type`, `unknown file
    type`, or `not a regular file`;
  - `input exceeds …` (over 20 MiB) or `output is … over the … byte limit`
    (over 5 MiB after stripping);
  - `cannot parse <fmt>: …`, `bad CRC …` or another structural reason: the
    file is truncated or corrupt. Write it again.

  Crop or shrink and send again, or send a text ping that describes the image.
  `strip self-check failed` is a bug in the helper, not in the file: report it.
- **The relay refuses the upload** (`relay error 422: media contains
  metadata`): something the helper keeps is still metadata to the relay. That
  is the fixed fallback of design.md gate 3 in openspec
  `agent-image-to-chat`; send a text ping meanwhile.
- **Sent, but no picture in the thread**: expected until
  `agent-image-to-chat-read` is built. The thread shows the caption only.
- **The notification shows a Markdown line instead of `🖼 caption`**: the
  listener logs `[listener] notify: image tags unreadable (…)` when it could
  not read the `imeta` tag; it then falls back to the plain text.

**The prune timer.** `ratatoskr-media-prune.timer` (daily 04:30) runs
`jobs/prune-media.sh`, which deletes image blobs older than 30 days on the
relay VM (`media-prune`, compose profile `maintenance`) and then checks the
store's size. It exits 1, and `scripts/check_timers.py` turns red, when:

- `[media-prune] prune failed on <host> (rc=…)` or `size check failed`: ssh to
  the relay VM or `sudo docker compose` failed. Try
  `ssh buzz-relay 'cd /opt/buzz-relay && sudo docker compose --profile maintenance run --rm media-prune size dst:buzz-media --json'`;
- `media store is <n> bytes after the prune, over the MEDIA_MAX_BYTES limit of
  <max>`: more images than expected, not deliberate growth. Twenty images a
  day for 30 days is about 0.6 GiB, so look for what is uploading.

`journalctl --user -u ratatoskr-media-prune.service` shows the last run. An
image that is older than 30 days is gone on purpose; its message text stays.

## An agent answers as if it does not know its role

Check what the listener actually reads, for every agent:

    python3 -c 'import sys; sys.path.insert(0, "agents"); import bootstrap
    for h in ["odin", "architect", "bouwer", "reviewer"]:
        d = bootstrap.fetch_def("https://raw.githubusercontent.com/MWest2020/handbook/main/docs/agents", h)
        print(h, len(d["system"]))'

`0` means the system prompt was not found. The prompt is the blockquote under
the `## Chat facet` heading of the handbook definition. From 2026-09-22 to
2026-10-22 all eight agents ran at 0, because the handbook's translation
changed the heading from `Chat-facet` to `Chat facet`. The parser now accepts
both, and the listener refuses to start an agent with an empty prompt; the
log says `no system prompt … NOT spawned`.

When the definition has a `## Contract` section, the prompt continues after
the blockquote with `YOUR CONTRACT` and that section (change `role-contracts`).
An agent that answers outside its role while its contract says "Not mine"
should therefore show the contract in that check. If it does not, the
listener has not yet seen the handbook merge: wait and check again before
restarting.

## Every habitat build fails on authentication

Habitat's workers run on one secret: `claude-oauth-token` in namespace
`agents`. It is a one-year token from `claude setup-token`, created
2026-09-05, so it expires around 2027-09-05. From 30 days before that, the
morning standup carries a `LET OP` line.

To renew it, the owner runs `claude setup-token` once (it needs a browser
login), then replaces the secret:

    ssh jumpy 'kubectl -n agents create secret generic claude-oauth-token \
      --from-literal=token=<token> --dry-run=client -o yaml | kubectl apply -f -'

The old ~8-hour session file (`claude-credentials`) is no longer pushed by
`orchestrator/dispatch-watch.sh` (2026-10-22). Nothing needs it.

## Development gotchas

- **Cold start.** The service worker serves the cached shell while the tailnet
  tunnel is not up yet. Anything in `init()` that needs the network must run
  after timers and listeners are set, and fail soft with a retry — otherwise
  the screen stays on "loading" forever (regression test:
  `chat/e2e/offline-boot.js`).
- **scrypt cost.** `hashlib.scrypt` with `N=2**15` exceeds OpenSSL's 32 MB
  limit ("memory limit exceeded"); use `N=2**14`.
- **`hidden` loses to any display rule.** `.field{display:flex}` overrides the
  `hidden` attribute, so the stylesheet needs `[hidden]{display:none!important}`.
  Test visibility with `offsetParent`, not the attribute.
- **Hooks in a worktree.** `git rev-parse --git-path hooks` returns the
  *shared* hooks directory, so a pre-push hook installed from one worktree
  blocks every other. Install per worktree via `extensions.worktreeConfig` and
  `core.hooksPath`.
