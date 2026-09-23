# Design — the hub delegates, the spokes work

## The shape

    Mark ──► odin (hub, #general)
               │  decides: answer, route, or delegate
               ├─ !route #channel ──────► a spoke agent, in its own channel
               ├─ !sessie <type> … ─────► a detached session; answer returns
               │                          in odin's voice, in this channel
               └─ "this goes to bouwer" ► !dispatch → habitat (Mark's gate)

Odin's job is **deciding which of these**, and staying free. Everything that
takes longer than a chat turn already runs detached.

## Why a session and not an "agent that fetches"

A spoke could be a second chat agent in its own channel. That is worse here:

- a chat turn is 150 s and synchronous within its own run; a session has a real
  budget and is detached by construction;
- a second agent needs a channel, an identity, membership and a mandate — four
  things to maintain for "look this up";
- the session mechanism already reports failure loudly, already bounds tools per
  type, and already returns in the hub's voice.

So the research spoke is a **session type**, not an agent.

## What the research spoke may read

This is the open question, and it deserves to be one. The five existing types
read a repository and may fetch the web *about* what they read. A research type
has no repository — its input is a URL or a question from the channel.

Two honest options:

- **Open web.** Matches what a human wants when dropping a link. Every fetched
  page is untrusted text written by a stranger, entering an agent whose output
  the hub reads.
- **Allow-list of domains.** Auditable, and useless the first time the link is
  somewhere unexpected.

Recommendation: **open web, with the marker rem below**, because an allow-list
that must be edited to read a link is the "self-imposed limitation" this change
exists to remove.

## The rem: fetched text is not an instruction

A session that reads the open web can read `!sessie …` or `!route …` inside a
page. The listener reads markers out of what is posted.

Rule: **a marker counts only on the first line of an agent's own answer.** Quoted
material further down is inert. This needs a test that posts an answer quoting a
marker and asserts that nothing started — a seam between two parts that each
have their own green tests is exactly where the failures of 11-13 September
lived (`AGENTS.md`).

Second rem, already present: `starters` per type. An injected marker can only
start what that identity is allowed to start.

## What odin says instead of "I can't"

Three sentences in the chat facet, not a new mechanism:

- a question about a repository → *"uitgezet bij een sessie"* + the marker;
- a link or a lookup → the research session;
- something to be built → *"dat loopt via @bouwer en habitat"* + what Mark must
  type. Never an apology for a road that exists.

## Rejected alternatives

**`WebFetch` in odin's definition.** The earlier version of this design. It makes
the hub do the work, and it blocks odin for the duration. Rejected on the
architecture, not on the risk.

**A permanent "fetcher" chat agent.** Four artefacts to maintain (channel,
identity, membership, mandate) for something the session mechanism already does
detached.

**Letting odin `!dispatch`.** The bridge deliberately gates on Mark's own
explicit command. Building is where a mistake is expensive; that gate stays.
