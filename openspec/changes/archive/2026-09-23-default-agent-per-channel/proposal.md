# Answering without being named

## Why

Mark, 2026-09-21: *"@odin moeten we achterwege kunnen laten, net alsof ik tegen
jou praat — 99% van de keren is dat toch het geval."*

Today the listener answers on two triggers (`listener.py`):

1. an **@mention** of an agent scoped to this channel;
2. a **follow-up**: no mention, but an agent posted within the last 10 messages
   *and* this channel is in that agent's own definition.

Rule 2 already covers a running conversation. What it does not cover is the
**cold start**: opening a channel and simply saying something. Then nothing
happens, and the human has to remember a handle to talk to a hub that has
exactly one job in that channel.

## What changes

A channel may name a **default agent**. When a human message has no mention and
no follow-up target, it goes to that agent.

Nothing else changes: an agent still never answers another agent, a marker line
(`!sessie`, `!route`) is still handled by its own path, and an agent still only
speaks where its definition and the relay membership allow.

## What it costs — say it out loud

- **Every human line in that channel becomes a paid turn.** Including "ok",
  including two people talking to each other. In #general that is the point; in
  a busy channel it would be a bill.
- **A message meant for another agent, typed without a handle, now goes to the
  default one.** The default agent should be a hub that routes, not a specialist.
- Therefore: **opt-in per channel**, never a global default.

## Not doing

- **A default in every channel.** #statistics and #escalatie are feeds; an agent
  that answers there is noise with a price tag.
- **Guessing intent with a classifier.** That is a model call to decide whether
  to make a model call, and it fails in the direction nobody notices: silently
  not answering.
