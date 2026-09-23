# The hub does not know it has spokes

## Why

Mark, 2026-09-21: *"Ik wil eigenlijk enkel met Odin spreken, maar odin moet niet
alles doen. Odin is de hub en niet de spokes. Idealiter vraagt odin een web fetch
agent om iets, en die zoekt het op, zodat odin ook weer vrij is."*

And: *"wat niet werkt is onnodige gesprekken met zelf opgelegde beperkingen."*

That last sentence is literally true, and the limitation is a sentence in a
file. Odin reports what its mandate says, and its mandate is older than the
machinery underneath it.

## What is already there

Measured in `agents/sessions.yml` and `docs/how-to/werksessies.md`, not assumed:

| | |
|---|---|
| `!sessie <type> <question>` | runs **detached** — the chat keeps working |
| odin on `starters` | 5 of the 6 types (everything except `build`) |
| `identity:` of every type | **odin** — the answer returns in the hub's own voice |
| `!route #channel` | hub forwards a human's own words to a spoke channel |
| `!dispatch <role> <change> <repo>` | the habitat bridge, gated on Mark's explicit command |

That is hub-and-spoke, asynchronous, with a return path. It works today.

## What is actually missing

**1. The mandate does not mention it.** `docs/agents/odin.md` says *"Odin maakt
of wijzigt zelf niets (conversatie-only, geen shell/repo)"* and lists exactly one
capability: `route_message`. `!sessie` does not appear. A hub that does not know
it has spokes answers "I can't" while standing on the delegation machinery.

**2. There is no spoke that looks things up.** All six session types are bound to
a repository (`workdir` + path-scoped read tools). `WebFetch` is in all of them,
but as a side tool for "can we borrow this?", not as a purpose. When Mark drops a
link, there is nobody to hand it to. *That* is the real content of "odin kan geen
web fetch" — not a missing permission on odin, but a missing spoke.

**3. Building has a path, and odin does not name it.** `!dispatch` exists,
bouwer guards habitat, the bridge refuses anything that is not Mark's own
explicit command. Asked for a pull request, odin should say *which road that
takes*, not apologise.

## What changes

1. **Odin's mandate gets its delegation capability written down**: it may start a
   session for a question it should not answer itself, and it says so in the
   channel ("uitgezet bij een sessie, ik meld me als er iets terugkomt").
2. **A research spoke**: one session type whose purpose is looking something up
   and reporting back. Not bound to a repository.
3. **Building stays with bouwer and habitat.** Nothing moves into the chat turn.

## Explicitly not

- **`WebFetch` in odin's own definition.** That was the earlier version of this
  proposal and it is wrong: it turns the hub into a spoke and keeps odin busy for
  the length of the fetch — the opposite of what was asked.
- **A credential, `Bash`, or a token in a chat turn.** `ENV_KEEP` exists because
  the listener carries every agent's nsec.
- **An MCP server.** A new trust boundary holding credentials, buying nothing a
  session does not already do. A "not yet" with a trigger: a verb a session
  cannot express.
