# SPDX-License-Identifier: MIT
"""A ceiling on concurrent scrypt calls on the open routes (auth_routes.py).

`ThreadingHTTPServer` (server.py) spawns a thread per connection, unbounded.
Every login, setup or invitation attempt costs at least one scrypt hash
(16 MiB, see auth_factors.py); unlimited concurrent attempts is unlimited
concurrent memory pressure — a real DoS risk on a small self-hosted VM.

A separate file for the same reason auth_throttle.py is separate from
auth_store.py: its own concern, and auth_routes.py stays under 200 lines.
"""
import threading

# Comfortably above real concurrent logins on a single-user/small-group
# installation, well below what turns 16 MiB-per-slot into a problem.
_SLOTS = threading.BoundedSemaphore(6)


def guarded(fn, *args, **kwargs):
    """Runs `fn(*args, **kwargs)` inside the bound.

    Returns None, without calling `fn`, when every slot is taken — the
    caller turns that into a 429 instead of queueing behind other people's
    hashes.
    """
    if not _SLOTS.acquire(blocking=False):
        return None
    try:
        return fn(*args, **kwargs)
    finally:
        _SLOTS.release()
