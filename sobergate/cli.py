"""CLI di SOBERGATE: test, check, status, run, install, uninstall, revoke."""

from __future__ import annotations

import argparse
import locale
import os
import shutil
import subprocess
import sys
import time

from . import __version__, battery, hooks, rawio, scoring, token_store


def _setup_terminal() -> None:
    if sys.platform == "win32":
        os.system("")  # abilita le sequenze ANSI nel terminale Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _detect_lang() -> str:
    loc = (locale.getlocale()[0] or os.environ.get("LANG", "")) or ""
    return "it" if loc.lower().startswith("it") else "en"


def _fmt_until(expires: float) -> str:
    return time.strftime("%H:%M", time.localtime(expires))


def cmd_test(args: argparse.Namespace) -> int:
    remaining = token_store.cooldown_remaining()
    if remaining > 0:
        print(f"⏳ Cooldown attivo: riprova tra {remaining / 60:.0f} minuti. Bevi un bicchiere d'acqua 💧")
        return 1
    if not rawio.stdin_is_console():
        print("❌ Il test richiede un terminale interattivo (TTY). Niente pipe, niente agenti.", file=sys.stderr)
        return 1

    lang = args.lang or _detect_lang()
    t = battery.TEXTS.get(lang, battery.TEXTS["en"])
    report = battery.run_battery(lang)

    print()
    print(f"   riflessi {report.breakdown['riflessi']}/100 · battitura {report.breakdown['battitura']}/100 · stroop {report.breakdown['stroop']}/100")
    for note in report.notes:
        print(f"   · {note}")
    print()

    if report.bot:
        print(t["bot"])
        token_store.start_cooldown()
        return 1
    if not report.passed:
        print(t["failed"].format(total=report.total, threshold=scoring.PASS_THRESHOLD,
                                 cooldown=int(token_store.FAIL_COOLDOWN_MIN)))
        token_store.start_cooldown()
        return 1

    payload = token_store.issue(report.total, hours=args.hours)
    print(t["passed"].format(total=report.total, until=_fmt_until(payload["expires"])))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    state, payload = token_store.status()
    if state == "valid":
        if not args.quiet and not args.hook:
            print(f"✅ token valido fino alle {_fmt_until(payload['expires'])} (punteggio {payload['score']}/100)")
        return 0

    reasons = {
        "missing": "nessun test di sobrietà superato",
        "expired": "il token di sobrietà è scaduto",
        "tampered": "token manomesso — riprova senza barare",
    }
    msg = f"🍺 SOBERGATE: {reasons[state]}. Apri un terminale e supera `sobergate test` prima di programmare."
    if args.hook == "claude":
        print(msg, file=sys.stderr)
        return 2  # exit 2 = Claude Code blocca il prompt e mostra il messaggio
    if not args.quiet:
        print(msg, file=sys.stderr)
    return 1


def cmd_status(_args: argparse.Namespace) -> int:
    state, payload = token_store.status()
    labels = {"valid": "✅ valido", "expired": "⌛ scaduto", "missing": "∅ assente", "tampered": "🚨 manomesso"}
    print(f"token: {labels[state]}")
    if payload:
        print(f"  punteggio: {payload['score']}/100")
        print(f"  scadenza:  {time.strftime('%Y-%m-%d %H:%M', time.localtime(payload['expires']))}")
    remaining = token_store.cooldown_remaining()
    if remaining > 0:
        print(f"cooldown: {remaining / 60:.0f} minuti rimanenti")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    state, _ = token_store.status()
    if state != "valid":
        print(f"🍺 SOBERGATE: `{args.command[0]}` è bloccato. Supera `sobergate test` prima.", file=sys.stderr)
        return 1
    exe = shutil.which(args.command[0])
    cmd = [exe, *args.command[1:]] if exe else args.command
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print(f"❌ comando non trovato: {args.command[0]}", file=sys.stderr)
        return 127


def cmd_install(args: argparse.Namespace) -> int:
    if args.claude:
        if hooks.install_claude():
            print(f"✅ Hook installato in {hooks.claude_settings_path()}")
            print("   Da ora ogni prompt di Claude Code richiede un token di sobrietà valido.")
        else:
            print("ℹ️  Hook già installato.")
        return 0
    print("Specifica il target: sobergate install --claude", file=sys.stderr)
    return 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    if args.claude:
        if hooks.uninstall_claude():
            print("✅ Hook rimosso. Claude Code è di nuovo libero (occhio al gin tonic).")
        else:
            print("ℹ️  Nessun hook da rimuovere.")
        return 0
    print("Specifica il target: sobergate uninstall --claude", file=sys.stderr)
    return 1


def cmd_revoke(_args: argparse.Namespace) -> int:
    token_store.revoke()
    print("Token revocato. Onestà apprezzata. 🫡")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sobergate", description="Don't drink and code: test di sobrietà che blocca i coding agent.")
    p.add_argument("--version", action="version", version=f"sobergate {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("test", help="esegui il test di sobrietà")
    t.add_argument("--hours", type=float, default=token_store.DEFAULT_HOURS, help="validità del token in ore (default 10)")
    t.add_argument("--lang", choices=["it", "en"], help="lingua del test (default: dal locale)")
    t.set_defaults(func=cmd_test)

    c = sub.add_parser("check", help="verifica il token (exit 0 = sobrio)")
    c.add_argument("--hook", choices=["claude"], help="modalità hook: exit 2 per bloccare il prompt")
    c.add_argument("--quiet", action="store_true")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("status", help="stato di token e cooldown")
    s.set_defaults(func=cmd_status)

    r = sub.add_parser("run", help="esegui un comando solo se sobrio: sobergate run codex")
    r.add_argument("command", nargs=argparse.REMAINDER, help="comando da proteggere")
    r.set_defaults(func=cmd_run)

    i = sub.add_parser("install", help="installa il blocco in un agente")
    i.add_argument("--claude", action="store_true", help="hook per Claude Code")
    i.set_defaults(func=cmd_install)

    u = sub.add_parser("uninstall", help="rimuovi il blocco")
    u.add_argument("--claude", action="store_true")
    u.set_defaults(func=cmd_uninstall)

    v = sub.add_parser("revoke", help="revoca il token corrente")
    v.set_defaults(func=cmd_revoke)
    return p


def main(argv: list = None) -> int:
    _setup_terminal()
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) == "run" and not args.command:
        print("uso: sobergate run <comando> [args…]", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrotto.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
