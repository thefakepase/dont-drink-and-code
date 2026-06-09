# SOBERGATE — Design

**Data:** 2026-06-10 · **Stato:** approvato (delega "fai tu" dell'utente)

## Obiettivo

Tool open source ("don't drink and code") che blocca Claude Code, Codex e qualsiasi coding agent se l'utente è ubriaco. Vincolo chiave posto dall'utente: **il test non dev'essere delegabile a un'AI** — se l'utente chiede al computer di superarlo, il computer non deve riuscirci.

## Decisioni

- **Rilevamento:** batteria interattiva da terminale (~60s), tre prove sensibili all'alcol: riflessi (reazione al "VIA!"), trascrizione di frase randomizzata (precisione + ritmo), test di Stroop (controllo inibitorio).
- **Anti-delega AI:** (1) il hook blocca l'agente *prima* che possa agire; (2) frasi generate a caso; (3) analisi del timing per-tasto — paste/injection (<15ms) o jitter nullo ⇒ flag bot e bocciatura immediata; (4) reazione mediana <100ms ⇒ bot; (5) richiesto TTY reale (`isatty`); (6) token HMAC non falsificabile senza il segreto locale.
- **Blocco:** token firmato in `~/.sobergate/` (validità 10h, configurabile). Claude Code: hook `UserPromptSubmit` che esce con codice 2 (blocca il prompt) se il token manca/è scaduto/manomesso. Altri agent: wrapper `sobergate run <cmd>`. Fallimento ⇒ cooldown 30 minuti.
- **Threat model dichiarato:** speed bump, non cassaforte. Un sobrio può disinstallare il hook; l'ubriaco è pigro e non ci riesce — è il comportamento voluto.
- **Stack:** Python ≥3.9, solo stdlib, cross-platform (msvcrt su Windows, termios/select su Unix). Packaging setuptools, console script `sobergate`. Lingue it/en (auto dal locale).

## Architettura

| Modulo | Responsabilità |
|---|---|
| `scoring.py` | funzioni pure di punteggio e flag bot — zero I/O, testate con pytest |
| `rawio.py` | input raw cross-platform con timestamp per-tasto |
| `battery.py` | le tre prove interattive, testi it/en, generazione frasi |
| `token_store.py` | token HMAC-SHA256, segreto locale, cooldown — testato |
| `hooks.py` | install/uninstall idempotente del hook in `~/.claude/settings.json` (con backup) — testato |
| `cli.py` | subcomandi: test, check, status, run, install, uninstall, revoke |

Soglia di passaggio: 70/100 (pesi: riflessi 35%, battitura 35%, Stroop 30%). Qualsiasi flag bot ⇒ bocciato a prescindere dal punteggio.

## Approcci scartati

- **Analisi continua della digitazione:** invasiva, falsi positivi, complessità alta.
- **Voce/scioglilingua al microfono:** ottimo anti-AI ma speech analysis pesante e fragile cross-platform — possibile v2.
- **Webcam (seguire un punto con lo sguardo):** dipendenze pesanti (OpenCV), problemi privacy — fuori scope.
