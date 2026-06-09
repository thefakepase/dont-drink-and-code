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


def _typewrite(text: str, wpm: float = 55, jitter: float = 0.04) -> None:
    """Stampa `text` un carattere alla volta con ritmo umano simulato."""
    rng = random.Random(42)
    delay = 60.0 / (wpm * 5)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(max(0.02, delay + rng.uniform(-jitter, jitter)))


def run_demo(lang: str = "it") -> scoring.ScoreReport:
    """Sessione dimostrativa scriptata: nessun input reale, solo animazione."""
    t = TEXTS.get(lang, TEXTS["en"])
    _println(t["intro"])
    time.sleep(0.8)

    # ── RIFLESSI ──────────────────────────────────────────────────────────────
    _println()
    _println(t["reaction_title"])
    latencies = []
    for ms in (231, 218, 244):
        _println(t["wait"])
        time.sleep(random.uniform(1.4, 2.2))
        _println(t["go"])
        time.sleep(ms / 1000)
        _println(f"   {ms} ms")
        latencies.append(ms / 1000)

    # ── BATTITURA ─────────────────────────────────────────────────────────────
    _println()
    _println(t["typing_title"])
    phrase = "la volpe 38 scivola sotto la luna felice" if lang == "it" else "the robot 38 slides under the happy moon"
    _println(f'   "{phrase}"')
    sys.stdout.write("   > ")
    sys.stdout.flush()
    _typewrite(phrase)
    sys.stdout.write("\n")
    sys.stdout.flush()

    # ── STROOP ────────────────────────────────────────────────────────────────
    colors = STROOP_COLORS[lang]
    names = list(colors)
    _println()
    _println(t["stroop_title"])
    _println(t["stroop_keys"] + "  ".join(f"[{k}]={name}" for name, (k, _) in colors.items()))

    demo_pairs = [
        ("rosso" if lang == "it" else "red",   "verde" if lang == "it" else "green"),
        ("verde" if lang == "it" else "green",  "blu"   if lang == "it" else "blue"),
        ("blu"   if lang == "it" else "blue",   "rosso" if lang == "it" else "red"),
        ("giallo" if lang == "it" else "yellow", "giallo" if lang == "it" else "yellow"),
        ("rosso" if lang == "it" else "red",   "blu"   if lang == "it" else "blue"),
    ]
    stroop_results = []
    for word, ink in demo_pairs:
        if word not in colors or ink not in colors:
            continue
        _, code = colors[ink]
        correct_key, _ = colors[ink]
        time.sleep(random.uniform(0.6, 1.0))
        sys.stdout.write(f"   \033[1;{code}m{word.upper()}\033[0m ? ")
        sys.stdout.flush()
        rt = random.uniform(0.75, 1.35)
        time.sleep(rt)
        correct = (ink == word) or random.random() > 0.15
        stroop_results.append((correct, rt))
        _println("✓" if correct else "✗")

    reaction = scoring.reaction_score(latencies)
    stamps = [0.18 * i + random.uniform(-0.03, 0.05) for i in range(len(phrase))]
    typing = scoring.typing_score(phrase, phrase, [100.0 + s for s in stamps])
    stroop = scoring.stroop_score(stroop_results)
    return scoring.composite(reaction, typing, stroop)


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
