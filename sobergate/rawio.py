"""Input da tastiera in modalità raw, cross-platform, con timestamp precisi.

La lettura tasto-per-tasto con perf_counter è ciò che permette di
distinguere un umano (jitter naturale) da input incollato o iniettato.
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager

WINDOWS = sys.platform == "win32"

if WINDOWS:
    import ctypes
    import msvcrt

    def stdin_is_console() -> bool:
        """isatty() su Windows è ingannabile dal device NUL: serve GetConsoleMode."""
        STD_INPUT_HANDLE = -10
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_ulong()
        return bool(kernel32.GetConsoleMode(handle, ctypes.byref(mode)))

    @contextmanager
    def raw_mode():
        yield

    def flush_input() -> None:
        while msvcrt.kbhit():
            msvcrt.getwch()

    def read_key(timeout: float = None):
        """Ritorna (carattere, timestamp) oppure (None, timestamp) a timeout scaduto."""
        start = time.perf_counter()
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # frecce/F-keys: scarta il secondo byte
                    if msvcrt.kbhit():
                        msvcrt.getwch()
                    continue
                return ch, time.perf_counter()
            if timeout is not None and (time.perf_counter() - start) >= timeout:
                return None, time.perf_counter()
            time.sleep(0.002)

else:
    import select
    import termios
    import tty

    def stdin_is_console() -> bool:
        return sys.stdin.isatty()

    @contextmanager
    def raw_mode():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def flush_input() -> None:
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)

    def read_key(timeout: float = None):
        """Da chiamare dentro raw_mode(). Stessa interfaccia della versione Windows."""
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if r:
            ch = sys.stdin.read(1)
            return ch, time.perf_counter()
        return None, time.perf_counter()


def read_line_timed(max_len: int = 200):
    """Legge una riga con echo manuale e registra il timestamp di ogni carattere.

    Ritorna (testo, timestamps, numero_backspace). Da usare dentro raw_mode().
    """
    chars: list = []
    stamps: list = []
    backspaces = 0
    while True:
        ch, t = read_key(None)
        if ch is None:
            continue
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(chars), stamps, backspaces
        if ch in ("\x08", "\x7f"):
            if chars:
                chars.pop()
                if stamps:
                    stamps.pop()
                backspaces += 1
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch.isprintable() and len(chars) < max_len:
            chars.append(ch)
            stamps.append(t)
            sys.stdout.write(ch)
            sys.stdout.flush()
