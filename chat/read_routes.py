# SPDX-License-Identifier: MIT
"""The GET routes under /api/ that read data: channels, agents, the work
overview, repos and PRs, pinned context and messages.

server.py decides whether a request gets this far (the session gate); this
module only answers it. Same shape as `statics.serve` and `auth_admin.route`:
True when this path is a read route and has been answered.

The invariant here: a user input error (unknown channel, bad repo) is a 400,
never a raw upstream error.
"""
import json
import re
from urllib.parse import parse_qs

import board   # work overview (snapshot from jobs/board.py)
import github  # GitHub read layer (repo/PR view + pinned context)
import push    # Web Push — VAPID public key
from buzzcli import buzz, list_channels_meta, valid_cid, author, ME
from fanout import channel_overview, agent_roster, channel_roster
import threads


def route(h, u):
    """True when `u` (the parsed URL) is a read route and has been sent."""
    if u.path == "/api/channels":
        return h._send(200, json.dumps(list_channels_meta())) or True
    if u.path == "/api/agents":
        return h._send(200, json.dumps({"agents": agent_roster()})) or True
    if u.path == "/api/channel-members":
        try:
            return h._send(200, json.dumps({"channels": channel_roster()})) or True
        except Exception as e:
            return h._send(502, json.dumps({"error": str(e)[:200]})) or True
    if u.path == "/api/push/vapid":
        return h._send(200, json.dumps({"key": push.vapid_public()})) or True
    if u.path == "/api/board":
        payload, code = board.read()
        return h._send(code, json.dumps(payload)) or True
    if u.path == "/api/overview":
        try:
            return h._send(200, json.dumps({"channels": channel_overview()})) or True
        except Exception as e:
            return h._send(502, json.dumps({"error": str(e)[:200]})) or True
    if u.path == "/api/repos":
        try:
            return h._send(200, json.dumps({"repos": github.list_repos()})) or True
        except Exception as e:
            return h._send(502, json.dumps({"error": str(e)[:200]})) or True
    if u.path == "/api/prs":
        repo = (parse_qs(u.query).get("repo") or [""])[0]
        if not github.valid_repo(repo):
            return h._send(400, json.dumps({"error": "repo: expected owner/name"})) or True
        try:
            return h._send(200, json.dumps({"prs": github.list_prs(repo)})) or True
        except Exception as e:
            return h._send(502, json.dumps({"error": str(e)[:200]})) or True
    if u.path == "/api/pr":
        q = parse_qs(u.query)
        repo = (q.get("repo") or [""])[0]
        num = (q.get("num") or [""])[0]
        if not github.valid_repo(repo) or not num.isdigit():
            return h._send(400, json.dumps({"error": "repo: owner/name, num: a number"})) or True
        try:
            return h._send(200, json.dumps(github.get_pr(repo, int(num)))) or True
        except Exception as e:
            return h._send(502, json.dumps({"error": str(e)[:200]})) or True
    if u.path == "/api/pinned":
        # Pinned context = knowledge/<channel>.md from the boomhuis repo (one
        # source of truth; update through git push). Empty = no pin.
        name = (parse_qs(u.query).get("channel") or [""])[0].lower()
        if not re.match(r"^[a-z0-9][a-z0-9_-]{0,30}$", name):
            return h._send(200, json.dumps({"content": ""})) or True
        try:
            return h._send(200, json.dumps(
                {"content": github.get_file(f"knowledge/{name}.md")})) or True
        except Exception:
            return h._send(200, json.dumps({"content": ""})) or True
    if u.path == "/api/messages":
        cid = (parse_qs(u.query).get("channel") or [""])[0]
        if not valid_cid(cid):
            return h._send(400, json.dumps({"error": "unknown channel"})) or True
        rc, out, err = buzz(["messages", "get", "--channel", cid])
        if rc != 0:
            return h._send(502, json.dumps({"error": err.strip()[:200]})) or True
        try:
            raw = json.loads(out)
        except Exception:
            raw = []
        msgs = raw if isinstance(raw, list) else raw.get("messages", [])
        out_msgs = [{
            "id": m.get("id"),
            "author": author(m.get("pubkey", "")),
            "mine": m.get("pubkey") == ME,
            "content": m.get("content", ""),
            "ts": m.get("created_at", 0),
            "reply_to": threads.reply_parent(m.get("tags")),
        } for m in msgs]
        out_msgs.sort(key=lambda x: x["ts"])
        return h._send(200, json.dumps({"messages": out_msgs})) or True
    return False

