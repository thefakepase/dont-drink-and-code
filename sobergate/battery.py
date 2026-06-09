"""La batteria interattiva di prove: riflessi, battitura, Stroop.

Tutto l'I/O passa da rawio; la valutazione è delegata alle funzioni
pure di scoring, così la logica resta testabile senza un terminale.
"""

from __future__ import annotations

import random
import sys
import time

from . import rawio, scoring

REACTION_ROUNDS = 3
STROOP_ROUNDS = 5
STROOP_TIMEOUT = 3.5
REACTION_TIMEOUT = 2.5

TEXTS = {
    "it": {
        "intro": "🍺 SOBERGATE — test di sobrietà (~60 secondi). Premi un tasto per iniziare.",
        "reaction_title": "[1/3] RIFLESSI — premi SPAZIO appena vedi VIA!",
        "wait": "   aspetta…",
        "go": "   >>> VIA! <<<",
        "early": "   ⚠️  troppo presto!",
        "missed": "   ⏱️  nessuna risposta",
        "typing_title": "[2/3] BATTITURA — trascrivi esattamente questa frase e premi INVIO:",
        "stroop_title": "[3/3] STROOP — premi il tasto del COLORE del testo, NON la parola scritta.",
        "stroop_keys": "   tasti: ",
        "passed": "✅ SOBRIO — punteggio {total}/100. Token valido fino alle {until}. Vai a programmare.",
        "failed": "🍺 BOCCIATO — punteggio {total}/100 (serve {threshold}). Bevi acqua, riprova tra {cooldown} minuti.",
        "bot": "🤖 SMASCHERATO — l'input non è umano. Bel tentativo di delegare il test a un'AI. Bocciato.",
    },
    "en": {
        "intro": "🍺 SOBERGATE — sobriety test (~60 seconds). Press any key to start.",
        "reaction_title": "[1/3] REFLEXES — press SPACE as soon as you see GO!",
        "wait": "   wait…",
        "go": "   >>> GO! <<<",
        "early": "   ⚠️  too early!",
        "missed": "   ⏱️  no response",
        "typing_title": "[2/3] TYPING — transcribe this sentence exactly, then press ENTER:",
        "stroop_title": "[3/3] STROOP — press the key for the COLOR of the text, NOT the written word.",
        "stroop_keys": "   keys: ",
        "passed": "✅ SOBER — score {total}/100. Token valid until {until}. Go code.",
        "failed": "🍺 FAILED — score {total}/100 (need {threshold}). Drink water, retry in {cooldown} minutes.",
        "bot": "🤖 BUSTED — this input is not human. Nice try delegating the test to an AI. Failed.",
    },
}

# Frasi generate a caso: nessuna risposta precompilabile.
PHRASE_POOLS = {
    "it": {
        "subj": ["il gatto", "la volpe", "un drago", "la nonna", "il robot", "lo squalo"],
        "verb": ["salta", "corre", "balla", "scivola", "vola", "rotola"],
        "where": ["sul divano", "in cucina", "verso il mare", "sotto la luna", "dietro la porta", "nel garage"],
        "adj": ["blu", "felice", "veloce", "stanco", "gigante", "silenzioso"],
    },
    "en": {
        "subj": ["the cat", "a fox", "the dragon", "grandma", "the robot", "a shark"],
        "verb": ["jumps", "runs", "dances", "slides", "flies", "rolls"],
        "where": ["on the sofa", "in the kitchen", "toward the sea", "under the moon", "behind the door", "in the garage"],
        "adj": ["blue", "happy", "fast", "tired", "giant", "silent"],
    },
}

STROOP_COLORS = {
    "it": {"rosso": ("r", 31), "verde": ("v", 32), "blu": ("b", 34), "giallo": ("g", 33)},
    "en": {"red": ("r", 31), "green": ("g", 32), "blue": ("b", 34), "yellow": ("y", 33)},
}


def make_phrase(lang: str, rng: random.Random) -> str:
    p = PHRASE_POOLS[lang]
    return (
        f"{rng.choice(p['subj'])} {rng.randint(10, 99)} {rng.choice(p['verb'])} "
        f"{rng.choice(p['where'])} {rng.choice(p['adj'])}"
    )


def _println(msg: str = "") -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def run_reaction(t: dict) -> scoring.TestResult:
    _println()
    _println(t["reaction_title"])
    latencies, false_starts = [], 0
    for _ in range(REACTION_ROUNDS):
        rawio.flush_input()
        _println(t["wait"])
        delay = random.uniform(1.5, 3.5)
        ch, _ = rawio.read_key(timeout=delay)
        if ch is not None:
            false_starts += 1
            _println(t["early"])
            continue
        rawio.flush_input()
        start = time.perf_counter()
        _println(t["go"])
        ch, pressed_at = rawio.read_key(timeout=REACTION_TIMEOUT)
        if ch is None:
            _println(t["missed"])
            latencies.append(REACTION_TIMEOUT)
        else:
            latency = pressed_at - start
            latencies.append(latency)
            _println(f"   {latency * 1000:.0f} ms")
    return scoring.reaction_score(latencies, false_starts)


def run_typing(t: dict, lang: str) -> scoring.TestResult:
    _println()
    _println(t["typing_title"])
    phrase = make_phrase(lang, random.Random())
    _println(f'   "{phrase}"')
    sys.stdout.write("   > ")
    sys.stdout.flush()
    rawio.flush_input()
    typed, stamps, backspaces = rawio.read_line_timed()
    return scoring.typing_score(phrase, typed, stamps, backspaces)


def run_stroop(t: dict, lang: str) -> scoring.TestResult:
    colors = STROOP_COLORS[lang]
    names = list(colors)
    _println()
    _println(t["stroop_title"])
    _println(t["stroop_keys"] + "  ".join(f"[{k}]={name}" for name, (k, _) in colors.items()))
    results = []
    for _ in range(STROOP_ROUNDS):
        word = random.choice(names)
        # 60% dei casi incongruente: è lì che l'ubriaco crolla.
        ink = random.choice([n for n in names if n != word]) if random.random() < 0.6 else word
        key, code = colors[ink]
        rawio.flush_input()
        sys.stdout.write(f"   \033[1;{code}m{word.upper()}\033[0m ? ")
        sys.stdout.flush()
        start = time.perf_counter()
        ch, pressed_at = rawio.read_key(timeout=STROOP_TIMEOUT)
        rt = (pressed_at - start) if ch is not None else STROOP_TIMEOUT
        correct = ch is not None and ch.lower() == key
        results.append((correct, rt))
        _println("✓" if correct else "✗")
    return scoring.stroop_score(results)


def run_battery(lang: str = "it") -> scoring.ScoreReport:
    t = TEXTS.get(lang, TEXTS["en"])
    _println(t["intro"])
    with rawio.raw_mode():
        rawio.flush_input()
        rawio.read_key(timeout=None)
        reaction = run_reaction(t)
        typing = run_typing(t, lang)
        stroop = run_stroop(t, lang)
    return scoring.composite(reaction, typing, stroop)
