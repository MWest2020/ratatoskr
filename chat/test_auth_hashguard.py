# SPDX-License-Identifier: EUPL-1.2
"""F4 (2026-09-12 security review): the ceiling on concurrent scrypt calls
(chat/auth_hashguard.py). Tests the boundary directly, not a live DoS."""
import unittest

import auth_hashguard as guard


class Guarded(unittest.TestCase):
    def test_a_free_slot_runs_the_call_and_returns_its_result(self):
        self.assertEqual(guard.guarded(lambda: 42), 42)

    def test_saturation_returns_none_without_calling(self):
        calls = []
        taken = [guard._SLOTS.acquire(blocking=False) for _ in range(6)]
        try:
            self.assertIsNone(guard.guarded(lambda: calls.append(1)))
        finally:
            for ok in taken:
                if ok:
                    guard._SLOTS.release()
        self.assertEqual(calls, [])

    def test_a_released_slot_is_usable_again(self):
        taken = [guard._SLOTS.acquire(blocking=False) for _ in range(6)]
        for ok in taken:
            if ok:
                guard._SLOTS.release()
        self.assertEqual(guard.guarded(lambda: "ok"), "ok")


if __name__ == "__main__":
    unittest.main()
