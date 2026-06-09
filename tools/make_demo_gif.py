"""Genera demo.gif: replay animato della sessione `sobergate test --demo`.

Renderer frame-per-frame con Pillow: nessuno strumento di screen
recording richiesto, output deterministico e riproducibile.
Uso: python tools/make_demo_gif.py [output.gif]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Palette (GitHub dark) ────────────────────────────────────────────────────
BG = "#0d1117"
CHROME = "#161b22"
FG = "#c9d1d9"
DIM = "#8b949e"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
YELLOW = "#d29922"
ORANGE = "#f0883e"

W, H = 780, 800
PAD_X, PAD_Y = 24, 56
LINE_H = 22
FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)
FONT_B = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 15)

CHECK, CROSS = "__CHECK__", "__CROSS__"

rng = random.Random(7)


class Term:
    """Stato del terminale: lista di righe, ogni riga è lista di span (testo, colore, bold)."""

    def __init__(self):
        self.lines = [[]]
        self.frames = []
        self.durations = []

    def span(self, text, color=FG, bold=False):
        self.lines[-1].append((text, color, bold))

    def newline(self):
        self.lines.append([])

    def line(self, text, color=FG, bold=False, hold=350):
        self.span(text, color, bold)
        self.newline()
        self.snap(hold)

    def type_text(self, text, color=FG, cps_delay=(45, 110)):
        for ch in text:
            self.span(ch, color)
            self.snap(rng.randint(*cps_delay))

    def snap(self, duration_ms):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # barra del titolo con i tre pallini
        d.rectangle([0, 0, W, 36], fill=CHROME)
        for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            d.ellipse([14 + i * 22, 12, 26 + i * 22, 24], fill=c)
        d.text((W // 2 - 60, 10), "sobergate", font=FONT, fill=DIM)

        y = PAD_Y
        for line in self.lines:
            x = PAD_X
            for text, color, bold in line:
                if text == CHECK:
                    d.line([x + 2, y + 9, x + 6, y + 13], fill=GREEN, width=2)
                    d.line([x + 6, y + 13, x + 13, y + 3], fill=GREEN, width=2)
                    x += 18
                    continue
                if text == CROSS:
                    d.line([x + 3, y + 4, x + 12, y + 13], fill=RED, width=2)
                    d.line([x + 12, y + 4, x + 3, y + 13], fill=RED, width=2)
                    x += 18
                    continue
                f = FONT_B if bold else FONT
                d.text((x, y), text, font=f, fill=color)
                x += d.textlength(text, font=f)
            y += LINE_H
        self.frames.append(img)
        self.durations.append(duration_ms)

    def save(self, path):
        self.frames[0].save(
            path,
            save_all=True,
            append_images=self.frames[1:],
            duration=self.durations,
            loop=0,
            optimize=True,
        )


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "demo.gif")
    t = Term()

    t.span("$ ", GREEN, bold=True)
    t.snap(600)
    t.type_text("sobergate test --demo")
    t.newline()
    t.snap(500)

    t.line("SOBERGATE — sobriety test (~60 seconds)", ORANGE, bold=True, hold=900)
    t.line("")

    t.line("[1/3] REFLEXES — press SPACE as soon as you see GO!", FG, bold=True, hold=600)
    for ms in (231, 218, 244):
        t.span("   wait", DIM)
        t.snap(300)
        for _ in range(3):
            t.span(".", DIM)
            t.snap(rng.randint(350, 650))
        t.newline()
        t.line("   >>> GO! <<<", GREEN, bold=True, hold=ms)
        t.line(f"   {ms} ms", DIM, hold=400)
    t.line("")

    t.line("[2/3] TYPING — transcribe this sentence exactly:", FG, bold=True, hold=600)
    phrase = "the robot 38 slides under the happy moon"
    t.line(f'   "{phrase}"', BLUE, hold=700)
    t.span("   > ", GREEN)
    t.snap(400)
    t.type_text(phrase, FG, cps_delay=(55, 140))
    t.newline()
    t.snap(500)
    t.line("")

    t.line("[3/3] STROOP — press the key for the COLOR, not the word.", FG, bold=True, hold=600)
    t.line("   keys: [r]=red  [g]=green  [b]=blue  [y]=yellow", DIM, hold=800)
    rounds = [("RED", GREEN, "g"), ("GREEN", BLUE, "b"), ("BLUE", RED, "r"),
              ("YELLOW", YELLOW, "y"), ("RED", BLUE, "b")]
    for word, ink, key in rounds:
        t.span("   ")
        t.span(word, ink, bold=True)
        t.span(" ? ", DIM)
        t.snap(rng.randint(700, 1200))
        t.span(key, FG, bold=True)
        t.span("  ")
        t.span(CHECK)
        t.newline()
        t.snap(350)
    t.line("")

    t.line("   reflexes 96/100 - typing 94/100 - stroop 91/100", DIM, hold=900)
    t.line("")
    t.span("SOBER", GREEN, bold=True)
    t.span("  ")
    t.span(CHECK)
    t.span("  score 94/100 - token valid 10h. ", FG)
    t.span("Go code.", GREEN, bold=True)
    t.newline()
    t.snap(1000)
    t.line("")
    t.span("Fail and you get a 30-minute cooldown. Your AI can't take it for you. ", DIM)
    t.snap(4500)

    t.save(out)
    print(f"{out} — {len(t.frames)} frames, {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
