# Tasks

## 1. Decide
- [ ] **For Mark.** Which channels get a default agent, and which handle?
      Proposal: `#general → odin`, and nothing else for now.

## 2. Build
- [ ] `default_agent` in `channels.yml`, read by `bootstrap.load_channels`.
- [ ] Third trigger in `listener.py`, after mention and follow-up.
- [ ] Startup fails loudly when a `default_agent` is not scoped to its channel.

## 3. The rem
- [ ] Test on the ORDER of the three triggers, not one test per trigger.
- [ ] Test that an agent message still triggers nothing.
