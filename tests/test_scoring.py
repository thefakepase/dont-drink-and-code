"""Test delle funzioni pure di punteggio: umano sobrio, ubriaco, bot."""

import pytest

from sobergate import scoring


def even_stamps(n, interval, jitter_seq=None):
    """Genera timestamp con intervallo fisso più un jitter opzionale."""
    t, out = 100.0, []
    for i in range(n):
        out.append(t)
        delta = interval + (jitter_seq[i % len(jitter_seq)] if jitter_seq else 0.0)
        t += delta
    return out


class TestLevenshtein:
    def test_identical(self):
        assert scoring.levenshtein("ciao", "ciao") == 0

    def test_substitution_and_insertion(self):
        assert scoring.levenshtein("gatto", "gatti") == 1
        assert scoring.levenshtein("gatto", "gattino") == 2

    def test_empty(self):
        assert scoring.levenshtein("", "abc") == 3


class TestReaction:
    def test_sober_human_passes(self):
        r = scoring.reaction_score([0.22, 0.25, 0.28])
        assert r.score == 100.0
        assert not r.bot

    def test_drunk_is_slow(self):
        r = scoring.reaction_score([0.65, 0.68, 0.62])
        assert r.score < 30.0
        assert not r.bot

    def test_bot_is_impossibly_fast(self):
        r = scoring.reaction_score([0.03, 0.05, 0.04])
        assert r.bot

    def test_false_starts_penalized(self):
        clean = scoring.reaction_score([0.25, 0.25, 0.25])
        dirty = scoring.reaction_score([0.25, 0.25, 0.25], false_starts=2)
        assert dirty.score == clean.score - 30.0

    def test_no_response_scores_zero(self):
        assert scoring.reaction_score([]).score == 0.0


class TestTyping:
    TARGET = "il gatto 47 salta sul divano blu"

    def human_stamps(self, n):
        jitter = [0.02, -0.03, 0.05, -0.01, 0.04, -0.02]
        return even_stamps(n, 0.18, jitter)

    def test_accurate_human_passes(self):
        typed = self.TARGET
        r = scoring.typing_score(self.TARGET, typed, self.human_stamps(len(typed)))
        assert r.score >= 90.0
        assert not r.bot

    def test_drunk_typos_fail(self):
        typed = "il gatot 74 slata sl divno bul"
        r = scoring.typing_score(self.TARGET, typed, self.human_stamps(len(typed)))
        assert r.score < scoring.PASS_THRESHOLD

    def test_pasted_text_is_bot(self):
        typed = self.TARGET
        r = scoring.typing_score(self.TARGET, typed, even_stamps(len(typed), 0.002))
        assert r.bot

    def test_robotic_rhythm_is_bot(self):
        typed = self.TARGET
        r = scoring.typing_score(self.TARGET, typed, even_stamps(len(typed), 0.12))
        assert r.bot

    def test_empty_input_scores_zero(self):
        assert scoring.typing_score(self.TARGET, "", []).score == 0.0

    def test_many_corrections_penalized(self):
        typed = self.TARGET
        stamps = self.human_stamps(len(typed))
        clean = scoring.typing_score(self.TARGET, typed, stamps, backspaces=0)
        messy = scoring.typing_score(self.TARGET, typed, stamps, backspaces=10)
        assert messy.score < clean.score


class TestStroop:
    def test_sober_human_passes(self):
        r = scoring.stroop_score([(True, 0.8)] * 4 + [(False, 1.1)])
        assert r.score >= 70.0
        assert not r.bot

    def test_drunk_confuses_word_and_color(self):
        r = scoring.stroop_score([(False, 2.5), (False, 2.8), (True, 2.2), (False, 3.0), (True, 2.6)])
        assert r.score < 40.0

    def test_perfect_instant_answers_are_bot(self):
        r = scoring.stroop_score([(True, 0.05)] * 5)
        assert r.bot

    def test_empty_scores_zero(self):
        assert scoring.stroop_score([]).score == 0.0


class TestComposite:
    def test_sober_passes(self):
        report = scoring.composite(
            scoring.TestResult(95.0), scoring.TestResult(90.0), scoring.TestResult(85.0)
        )
        assert report.passed
        assert not report.bot

    def test_drunk_fails(self):
        report = scoring.composite(
            scoring.TestResult(40.0), scoring.TestResult(50.0), scoring.TestResult(30.0)
        )
        assert not report.passed

    def test_any_bot_flag_fails_even_with_high_score(self):
        report = scoring.composite(
            scoring.TestResult(100.0, bot=True), scoring.TestResult(100.0), scoring.TestResult(100.0)
        )
        assert report.bot
        assert not report.passed

    def test_threshold_boundary(self):
        report = scoring.composite(
            scoring.TestResult(70.0), scoring.TestResult(70.0), scoring.TestResult(70.0)
        )
        assert report.total == 70
        assert report.passed
