# assistent — chat-agent (dunne claude -p-listener)

De eerste chat-native agent van het boomhuis. `listener.py` luistert de kanalen
af via buzz-cli; bij een `@assistent`-mention draait het `claude -p`
(sub-first, jouw abonnement) met wat kanaalcontext en post het antwoord terug
als de identiteit `assistent`.

## Waarom dit patroon (niet buzz-acp)
buzz-acp eist een API-key; `claude -p` rijdt op je abonnement. Dun, saai,
auditeerbaar, sub-wissel-bestendig (`claude login`). Zie [[boomhuis-project]].

## Draaien (op agent-lxc: claude + buzz + age-key aanwezig)
    AGENT_NSEC=<assistent-nsec, sops -d secrets/identities.yaml> \
    BUZZ_RELAY_URL=ws://192.168.178.60:3000 \
    BUZZ_BIN=$HOME/.local/bin/buzz CLAUDE_BIN=$(which claude) \
    python3 agents/assistent/listener.py

## Vereisten die eenmalig geregeld zijn
- assistent in identities.yml + secrets/identities.yaml (SOPS)
- relay-lid: buzz-admin add-member (pubkey 378aaf0f…)
- kanaal-lid (rol bot) in alle 6 kanalen: buzz channels add-member --role bot
- chat-backend injecteert @assistent -> pubkey bij het posten (server.py HANDLES)

## Nog te doen (hardening / fase 2)
- systemd-service (nu nohup, niet reboot-vast); AGENT_NSEC uit SOPS bij start.
- meer rollen (architect-sparring, marketing) = kopie met eigen identiteit +
  systemprompt. Kanaal-per-sessie: een agent per tmux/habitat-run-kanaal.
- budget/rate-caps expliciet (nu: alleen op @mention, 120s cap per beurt).
