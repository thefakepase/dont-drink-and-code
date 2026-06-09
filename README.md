# 🍺 SOBERGATE — Don't Drink and Code

[![CI](https://github.com/thefakepase/dont-drink-and-code/actions/workflows/ci.yml/badge.svg)](https://github.com/thefakepase/dont-drink-and-code/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Works on: Claude Code](https://img.shields.io/badge/blocks-Claude%20Code%20%7C%20Codex%20%7C%20any%20AI%20agent-red.svg)](#)

> *If you're drunk you can't code. And your AI can't take the test for you.*
>
> Se sei ubriaco non puoi programmare. E nemmeno la tua AI può farlo al posto tuo.

**SOBERGATE** is a terminal sobriety test that **blocks Claude Code, Codex, and any AI coding agent** until you prove you're sober. No sensors, no breathalyzer: 60 seconds of tests that a drunk person fails and that no AI can pass on your behalf.

---

## English TL;DR

A terminal sobriety test that **blocks Claude Code, Codex and any coding agent** until you prove you're sober. Three challenges (~60s): reaction time, randomized transcription with keystroke-timing analysis, and a Stroop test. Pass → signed HMAC token valid 10 hours. Fail → 30-minute cooldown. An AI can't take it for you: phrases are randomized, input timing is analyzed for human jitter, and pasted/injected input gets you **busted as a bot** 🤖. Install: `pipx install .` then `sobergate install --claude`.

---

## Come funziona

```
$ sobergate test

🍺 SOBERGATE — test di sobrietà (~60 secondi). Premi un tasto per iniziare.

[1/3] RIFLESSI — premi SPAZIO appena vedi VIA!
   aspetta…
   >>> VIA! <<<
   243 ms

[2/3] BATTITURA — trascrivi esattamente questa frase e premi INVIO:
   "la volpe 38 scivola sotto la luna felice"
   > la volpe 38 scivola sotto la luna felice

[3/3] STROOP — premi il tasto del COLORE del testo, NON la parola scritta.
   tasti: [r]=rosso  [v]=verde  [b]=blu  [g]=giallo
   VERDE ? ✓        ← scritto in rosso: dovevi premere [r]

   riflessi 96/100 · battitura 91/100 · stroop 88/100

✅ SOBRIO — punteggio 92/100. Token valido fino alle 23:41. Vai a programmare.
```

Le tre prove sono scelte perché l'alcol le degrada in modo misurabile:

| Prova | Cosa misura | Perché l'ubriaco fallisce |
|---|---|---|
| **Riflessi** | tempo di reazione al "VIA!" | l'alcol rallenta la reazione oltre i ~500ms |
| **Battitura** | precisione + ritmo su una frase **generata a caso** | errori, lettere invertite, ritmo irregolare |
| **Stroop** | parola "VERDE" scritta in rosso: premi il tasto del *colore* | il controllo inibitorio è la prima cosa che l'alcol spegne |

Superi il test → token firmato HMAC in `~/.sobergate/`, valido 10 ore.
Fallisci → cooldown di 30 minuti. Bevi acqua. 💧

## Perché un'AI non può farlo al posto tuo

L'idea chiave: ubriaco, potresti chiedere a Claude *"fai tu il test"*. Non funzionerà:

1. **Il test gira prima dell'agente.** Il hook blocca Claude Code *all'avvio del prompt*: l'AI che vorresti usare per barare è esattamente quella bloccata.
2. **Frasi randomizzate.** Niente risposte precompilate o script preparati prima.
3. **Analisi del timing dei tasti.** L'input umano ha jitter naturale; testo incollato o iniettato arriva a intervalli impossibili (<15ms) o innaturalmente regolari → `🤖 SMASCHERATO`.
4. **Reazioni sotto i 100ms = bot.** Nessun umano è così veloce; uno script sì.
5. **Serve un vero TTY.** Niente pipe, niente stdin redirect: `sobergate test < risposte.txt` viene rifiutato.
6. **Token firmato.** Non puoi (e non può l'AI) scrivere a mano un `token.json` valido: la firma HMAC usa un segreto locale e ogni manomissione viene rilevata.

### Modello di minaccia (onestà prima di tutto)

SOBERGATE è un **dosso artificiale, non una cassaforte**. Un utente sobrio e determinato può sempre disinstallare il hook (`sobergate uninstall --claude`) — ed è giusto così. La scommessa è un'altra: *l'ubriaco è pigro*. Tra superare un test che continua a bocciarlo e ricordarsi come smontare il sistema, sceglierà il divano. Ed è esattamente il risultato che volevamo.

## Installazione

Richiede Python ≥ 3.9. Zero dipendenze esterne.

```bash
git clone https://github.com/thefakepase/dont-drink-and-code.git
cd dont-drink-and-code
pipx install .        # oppure: pip install .
```

### Blocca Claude Code (hook nativo)

```bash
sobergate install --claude
```

Aggiunge un hook `UserPromptSubmit` a `~/.claude/settings.json`: ogni prompt senza token valido viene rifiutato con il messaggio *"supera `sobergate test` prima di programmare"*. Rimozione: `sobergate uninstall --claude`.

### Blocca Codex / Aider / qualsiasi altro agent (wrapper)

```bash
sobergate run codex
sobergate run aider --model gpt-5
```

Oppure rendilo permanente con un alias nella shell:

```powershell
# PowerShell ($PROFILE)
function codex { sobergate run codex @args }
```

```bash
# bash/zsh (~/.bashrc, ~/.zshrc)
alias codex='sobergate run codex'
```

## Comandi

| Comando | Descrizione |
|---|---|
| `sobergate test` | esegue il test (opzioni: `--hours 4`, `--lang en`) |
| `sobergate check` | exit 0 se sobrio, 1 altrimenti — usalo negli script |
| `sobergate status` | stato del token e del cooldown |
| `sobergate run <cmd>` | esegue un comando solo con token valido |
| `sobergate install --claude` | installa il blocco in Claude Code |
| `sobergate uninstall --claude` | rimuove il blocco |
| `sobergate revoke` | revoca il token (per i giorni di onestà preventiva) |

## FAQ

**È uno scherzo?** Sì e no. Il tono è giocoso, ma il test misura cose reali (reazione, coordinazione, controllo inibitorio) e il blocco funziona davvero.

**Posso usarlo per altro?** Certo: sostituisci "ubriaco" con "troppo stanco per fare deploy alle 3 di notte" e il sistema è identico. `sobergate test --hours 2` prima di toccare la produzione.

**Rileva davvero l'alcol?** Misura il deterioramento psicomotorio, che è ciò che conta per programmare. Non sostituisce un etilometro e soprattutto **non autorizza a guidare**. Mai.

**Falsi positivi?** Se sei sobrio ma il test ti boccia, o stai digitando con un dito solo o è il caso di andare a dormire comunque.

## Licenza

MIT — bevi responsabilmente, committa ancora più responsabilmente.
