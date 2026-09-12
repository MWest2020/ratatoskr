# SPDX-License-Identifier: EUPL-1.2
"""Agent/channel actions for the chat backend, separate from server.py (routing)
so both stay under the ≤200-line convention. Every function returns (status,
payload).
"""
import json
import re
import sys

import roster
from buzzcli import ADMIN_OFF, buzz, buzz_admin, channel_member_pubkeys, valid_cid

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")
_MENTION_ERR = re.compile(r"mention '@([A-Za-z0-9_-]+)' does not match")


def _a_member_of(cid):
    """A pubkey that really IS a MEMBER of THIS channel (anchor for the forced
    mention). Deterministic (sorted) and preferably a non-agent member, so the
    anchor cannot be confused with an agent at all. The member is not @-ed in the
    content, so the listener (which triggers on @handle in the text) does not
    react to it; the preference is an extra belt."""
    members = sorted(p for p in channel_member_pubkeys(cid) if p)  # stabiel per call
    if not members:
        return None
    agents = {a["pubkey"] for a in roster.chat_agents()}
    return next((p for p in members if p not in agents), members[0])


def add_agent(cid, name):
    """Add an agent (name→pubkey from the registry) as a bot."""
    if not valid_cid(cid):
        return 400, {"error": "unknown channel"}
    pk = roster.agent_pubkey(name)
    if not pk:
        return 404, {"error": f"'{name}' is not an agent (sessions and mark are not added this way)"}
    rc, out, err = buzz_admin(["channels", "add-member", "--channel", cid,
                               "--pubkey", pk, "--role", "bot"])
    if rc is None:
        return 503, {"error": ADMIN_OFF}
    if rc != 0:
        return 502, {"error": (err or out).strip()[:200]}
    return 200, {"ok": True, "name": name}


def send(cid, content, force=False):
    """Send a message. Without --mention the relay resolves an @agent to the
    member and triggers it; an @name that is not a member gives a 409 with a
    choice (add it when it is an agent, or 'send anyway'). With `force` we pass a
    genuinely existing channel member (`_a_member_of`) as the anchor mention so
    ALL @words become presentation-only — for @here, a pasted handle, and so on."""
    if not valid_cid(cid):
        return 400, {"error": "unknown channel"}
    content = (content or "").strip()
    if not content:
        return 400, {"error": "empty message"}
    args = ["messages", "send", "--channel", cid, "--content", "-"]
    if force:
        anchor = _a_member_of(cid)
        if anchor:
            args += ["--mention", anchor]  # a real member → @words presentation-only
    rc, out, err = buzz(args, stdin=content)
    if rc == 0:
        return 200, {"ok": True}
    m = _MENTION_ERR.search((err or "") + (out or ""))
    if m:
        who = m.group(1)
        return 409, {
            "missing_agent": who,
            "known": roster.agent_pubkey(who) is not None,  # only real agents → add
            "can_force": True,                              # 'send anyway' is allowed
            "channel": cid,
        }
    return 502, {"error": (err or out or "").strip()[:200]}


def _add_hub(create_out):
    """Best effort: the hub agent as a member of a freshly created channel. Must
    NEVER raise — the channel already exists. Fails quietly but visibly (log to
    stderr, return None/False), so an add error does not topple the whole create.

    The hub is looked up by ROLE (`meta-agent`), not by name: after the rename
    coordinator -> odin the name variant gave `geen cid/pubkey` and no new channel
    got a hub any more."""
    try:
        d = json.loads(create_out)
        cid = d.get("channel_id") or d.get("id")  # relay gebruikt beide
        co = roster.hub_pubkey()
        if not (cid and co):
            sys.stderr.write("[create] hub-add overgeslagen: geen cid/hub-pubkey\n")
            return False
        ar, _o, ae = buzz_admin(["channels", "add-member", "--channel", cid,
                                 "--pubkey", co, "--role", "bot"])
        if ar is None or ar != 0:
            sys.stderr.write(f"[create] hub-add faalde: {(ae or _o).strip()[:120]}\n")
        return ar == 0
    except Exception as e:  # noqa: BLE001 — the create succeeded; the add is a side issue
        sys.stderr.write(f"[create] hub-add fout: {e}\n")
        return False


def create_channel(name):
    """Create an open channel and add the hub agent by default (best effort: if
    the add fails the channel still exists; `hub_added` says so)."""
    name = (name or "").strip().lower()
    if not _NAME_RE.match(name):
        return 400, {"error": "name: a-z 0-9 _ - (max 31)"}
    rc, out, err = buzz_admin(["channels", "create", "--name", name,
                               "--type", "stream", "--visibility", "open"])
    if rc is None:
        return 503, {"error": ADMIN_OFF}
    if rc != 0:
        return 502, {"error": err.strip()[:200]}
    return 200, {"ok": True, "name": name, "hub_added": _add_hub(out)}
