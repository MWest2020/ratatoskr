# SPDX-License-Identifier: MIT
"""The action layer: who signs what, and what happens when the relay says no.

Two things that really went wrong here and that these tests pin down: channel
management must NEVER be signed with Mark's key (fail-closed instead of falling
back), and the hub is looked up by role — by name that broke silently after the
rename coordinator -> odin, after which every new channel came into being without
a hub.
"""
import json
import unittest

import actions
import buzzcli
import roster


class Fake:
    """Replaces buzz/buzz_admin and remembers the calls."""

    def __init__(self, answer=(0, "", ""), admin_off=False):
        self.answer, self.admin_off, self.calls = answer, admin_off, []

    def buzz(self, args, stdin=None, timeout=25, key=None):
        self.calls.append(("buzz", args, key))
        return self.answer

    def admin(self, args, stdin=None, timeout=25):
        self.calls.append(("admin", args, None))
        if self.admin_off:
            return None, "", buzzcli.ADMIN_OFF
        return self.answer


class Base(unittest.TestCase):
    def install(self, fake, cids=("c1",), agents=None, hub="pk-odin"):
        self.old = (actions.buzz, actions.buzz_admin, actions.valid_cid,
                    roster.agent_pubkey, roster.hub_pubkey, actions.channel_member_pubkeys)
        actions.buzz, actions.buzz_admin = fake.buzz, fake.admin
        actions.valid_cid = lambda c: c in cids
        actions.channel_member_pubkeys = lambda c: {"pk-lid": "member"}
        roster.agent_pubkey = lambda n: (agents or {}).get(n)
        roster.hub_pubkey = lambda: hub

    def tearDown(self):
        (actions.buzz, actions.buzz_admin, actions.valid_cid,
         roster.agent_pubkey, roster.hub_pubkey, actions.channel_member_pubkeys) = self.old


class ChannelAdminTest(Base):
    def test_create_signs_as_orchestrator_not_as_mark(self):
        fake = Fake((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.install(fake)
        code, _ = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 200)
        kinds = {c[0] for c in fake.calls}
        self.assertEqual(kinds, {"admin"})            # not a single plain buzz call

    def test_without_the_orchestrator_key_there_is_no_silent_fallback(self):
        fake = Fake(admin_off=True)
        self.install(fake)
        code, payload = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 503)
        self.assertIn("BUZZ_ORCHESTRATOR_KEY", payload["error"])
        self.assertNotIn("buzz", {c[0] for c in fake.calls})  # nothing with mark's key

    def test_the_name_is_validated_before_the_relay(self):
        fake = Fake(); self.install(fake)
        for name in ("", "met spatie", "a" * 40, "-begintfout", "../x", "a/b"):
            code, _ = actions.create_channel(name)
            self.assertEqual(code, 400, name)
        self.assertEqual(fake.calls, [])              # nothing reached the relay

    def test_capitals_and_spaces_are_normalised(self):
        # Deliberately not an error: the user types "Bouw " and gets #bouw.
        fake = Fake((0, json.dumps({"channel_id": "n"}), "")); self.install(fake)
        code, payload = actions.create_channel("  Bouw  ")
        self.assertEqual((code, payload["name"]), (200, "bouw"))

    def test_the_hub_is_added_to_a_new_channel(self):
        fake = Fake((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.install(fake)
        _, payload = actions.create_channel("bouwoverleg")
        self.assertTrue(payload["hub_added"])
        add = [c for c in fake.calls if c[1][:2] == ["channels", "add-member"]]
        self.assertEqual(add[0][1][5], "pk-odin")     # --pubkey of the hub

    def test_the_create_does_not_fail_without_a_hub(self):
        # The add is best effort: the channel already exists. Visible in the answer.
        fake = Fake((0, json.dumps({"channel_id": "nieuw"}), ""))
        self.install(fake, hub=None)
        code, payload = actions.create_channel("bouwoverleg")
        self.assertEqual(code, 200)
        self.assertFalse(payload["hub_added"])


class AddAgentTest(Base):
    def test_only_known_agents(self):
        fake = Fake(); self.install(fake, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("c1", "onbekend")[0], 404)
        self.assertEqual(fake.calls, [])

    def test_an_unknown_channel_is_refused(self):
        fake = Fake(); self.install(fake, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("bestaat-niet", "bouwer")[0], 400)

    def test_adding_signs_as_orchestrator(self):
        fake = Fake(); self.install(fake, agents={"bouwer": "pk-b"})
        self.assertEqual(actions.add_agent("c1", "bouwer")[0], 200)
        self.assertEqual({c[0] for c in fake.calls}, {"admin"})


class SendTest(Base):
    def test_empty_content_never_reaches_the_relay(self):
        fake = Fake(); self.install(fake)
        self.assertEqual(actions.send("c1", "   ")[0], 400)
        self.assertEqual(fake.calls, [])

    def test_an_unknown_channel_is_refused(self):
        fake = Fake(); self.install(fake)
        self.assertEqual(actions.send("weg", "hoi")[0], 400)

    def test_a_message_signs_with_the_process_identity(self):
        fake = Fake(); self.install(fake)
        self.assertEqual(actions.send("c1", "hoi")[0], 200)
        self.assertEqual({c[0] for c in fake.calls}, {"buzz"})  # mark, not the orchestrator

    def test_an_unknown_mention_returns_a_choice(self):
        err = (1, "", "mention '@bouwer' does not match any channel member")
        fake = Fake(err); self.install(fake, agents={"bouwer": "pk-b"})
        code, payload = actions.send("c1", "hoi @bouwer")
        self.assertEqual(code, 409)
        self.assertEqual(payload["missing_agent"], "bouwer")
        self.assertTrue(payload["known"])            # exists -> "add" is allowed
        self.assertTrue(payload["can_force"])

    def test_an_unknown_mention_that_is_not_an_agent(self):
        err = (1, "", "mention '@niemand' does not match any channel member")
        fake = Fake(err); self.install(fake, agents={})
        _, payload = actions.send("c1", "hoi @niemand")
        self.assertFalse(payload["known"])           # only "send anyway"

    def test_force_uses_a_real_member_as_anchor(self):
        fake = Fake(); self.install(fake)
        actions.send("c1", "hoi @here", force=True)
        args = fake.calls[0][1]
        self.assertIn("--mention", args)
        self.assertEqual(args[args.index("--mention") + 1], "pk-lid")

    def test_another_relay_error_stays_a_502(self):
        fake = Fake((1, "", "relay down")); self.install(fake)
        code, payload = actions.send("c1", "hoi")
        self.assertEqual(code, 502)
        self.assertIn("relay down", payload["error"])


if __name__ == "__main__":
    unittest.main()
