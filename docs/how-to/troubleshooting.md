---
status: actief
last_reviewed: 2026-10-22
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
