"""Funzioni pure di punteggio: nessun I/O, completamente testabili.

Ogni prova produce (punteggio 0-100, bot_sospetto, note).
Il punteggio composito decide se l'utente è sobrio; i flag "bot"
scattano quando l'input è troppo perfetto per essere umano
(incollato, jitter nullo, reazioni sotto la soglia fisiologica).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

PASS_THRESHOLD = 70

# Soglie fisiologiche: sotto questi tempi nessun umano risponde.
MIN_HUMAN_REACTION = 0.10  # secondi
MIN_HUMAN_KEY_INTERVAL = 0.015  # secondi tra due tasti
MIN_HUMAN_JITTER = 0.008  # deviazione standard degli intervalli


@dataclass
class TestResult:
    score: float
    bot: bool = False
    notes: list = field(default_factory=list)


@dataclass
class ScoreReport:
    total: int
    passed: bool
    bot: bool
    breakdown: dict
    notes: list


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _linear(value: float, best: float, worst: float, max_score: float) -> float:
    """max_score se value <= best, 0 se value >= worst, lineare in mezzo."""
    if value <= best:
        return max_score
    if value >= worst:
        return 0.0
    return max_score * (worst - value) / (worst - best)


def reaction_score(latencies: list, false_starts: int = 0) -> TestResult:
    """latencies: secondi tra il VIA! e la pressione del tasto."""
    if not latencies:
        return TestResult(0.0, notes=["nessuna risposta al test di reazione"])
    med = statistics.median(latencies)
    bot = med < MIN_HUMAN_REACTION
    notes = []
    if bot:
        notes.append(f"reazione mediana {med * 1000:.0f}ms: nessun umano è così veloce")
    score = _linear(med, best=0.25, worst=0.70, max_score=100.0)
    if false_starts:
        score -= 15.0 * false_starts
        notes.append(f"{false_starts} partenze anticipate")
    if med > 0.50 and not bot:
        notes.append("riflessi lenti")
    return TestResult(_clamp(score), bot, notes)


def typing_score(target: str, typed: str, timestamps: list, backspaces: int = 0) -> TestResult:
    """timestamps: perf_counter di ogni carattere stampabile digitato."""
    notes = []
    if not typed or len(timestamps) < 2:
        return TestResult(0.0, notes=["nessun testo digitato"])

    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    accuracy = 1.0 - levenshtein(target, typed) / max(len(target), 1)
    mean_int = statistics.mean(intervals)

    fast = sum(1 for i in intervals if i < MIN_HUMAN_KEY_INTERVAL)
    paste = len(intervals) >= 4 and fast / len(intervals) > 0.3
    flat = len(intervals) >= 5 and statistics.pstdev(intervals) < MIN_HUMAN_JITTER
    bot = paste or flat
    if paste:
        notes.append("testo incollato o iniettato: i tasti sono arrivati troppo ravvicinati")
    if flat:
        notes.append("ritmo di battitura innaturalmente regolare")

    acc_score = _clamp((accuracy - 0.75) / (0.98 - 0.75) * 75.0, 0.0, 75.0)
    speed_score = _linear(mean_int, best=0.35, worst=0.90, max_score=25.0)
    penalty = min(10.0, 2.0 * max(0, backspaces - 3))
    if accuracy < 0.85:
        notes.append(f"precisione {accuracy * 100:.0f}%: troppi errori")
    if penalty:
        notes.append(f"{backspaces} correzioni")
    return TestResult(_clamp(acc_score + speed_score - penalty), bot, notes)


def stroop_score(results: list) -> TestResult:
    """results: lista di (corretto: bool, tempo_risposta: float)."""
    if not results:
        return TestResult(0.0, notes=["test di Stroop non eseguito"])
    n = len(results)
    correct = sum(1 for ok, _ in results if ok)
    rts = [rt for _, rt in results]
    med = statistics.median(rts)
    bot = correct == n and med < 0.18
    notes = []
    if bot:
        notes.append("risposte Stroop perfette e istantanee: profilo da macchina")
    acc_score = correct / n * 70.0
    speed_score = _linear(med, best=1.0, worst=2.8, max_score=30.0)
    if correct < n * 0.6:
        notes.append(f"Stroop {correct}/{n}: il cervello sta confondendo parola e colore")
    return TestResult(_clamp(acc_score + speed_score), bot, notes)


def composite(reaction: TestResult, typing: TestResult, stroop: TestResult) -> ScoreReport:
    total = round(0.35 * reaction.score + 0.35 * typing.score + 0.30 * stroop.score)
    bot = reaction.bot or typing.bot or stroop.bot
    notes = reaction.notes + typing.notes + stroop.notes
    return ScoreReport(
        total=total,
        passed=total >= PASS_THRESHOLD and not bot,
        bot=bot,
        breakdown={
            "riflessi": round(reaction.score),
            "battitura": round(typing.score),
            "stroop": round(stroop.score),
        },
        notes=notes,
    )
