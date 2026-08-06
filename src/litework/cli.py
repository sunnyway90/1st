"""LiteWork CLI — light, modular team collaboration."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from litework import __version__
from litework.core.plugins import get_registry
from litework.core.store import Store


def _default_db() -> Path:
    override = os.environ.get("LITEWORK_DB")
    if override:
        return Path(override)
    return Path.home() / ".litework" / "litework.db"


def _module_list(store: Store) -> int:
    registry = get_registry()
    known = {m.name: m for m in registry.all()}
    for name in known:
        if store.get_module(name) is None:
            store.set_module(name, enabled=True)
    print("NAME\tENABLED\tREQUIRED\tDESCRIPTION")
    for name in sorted(known):
        mod = known[name]
        state = store.get_module(name)
        enabled = True if state is None else state.enabled
        req = "yes" if mod.required else "no"
        print(f"{name}\t{str(enabled).lower()}\t{req}\t{mod.description}")
    return 0


def _module_set(store: Store, name: str, enabled: bool) -> int:
    mod = get_registry().get(name)
    if not mod:
        print(f"error: unknown module: {name}")
        print(f"available: {', '.join(get_registry().names())}")
        return 1
    if mod.required and not enabled:
        print(f"error: module '{name}' is required and cannot be disabled")
        return 1
    store.set_module(name, enabled=enabled)
    print(f"{'enabled' if enabled else 'disabled'} module: {name}")
    return 0


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, str]]:
    """Build CLI. Returns parser and a mutable db path box for store factories."""
    db_box: dict[str, str] = {"db": str(_default_db())}

    def store_factory() -> Store:
        return Store(db_box["db"])

    parser = argparse.ArgumentParser(
        prog="litework",
        description=(
            "LiteWork: lightweight modular collaboration for small teams "
            "(~10 people × ~10 companies). Offer/book work time and share progress."
        ),
    )
    parser.add_argument(
        "--db",
        default=str(_default_db()),
        help="SQLite database path (or set LITEWORK_DB)",
    )
    parser.add_argument(
        "--version", action="version", version=f"litework {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    mod = sub.add_parser("module", help="List / enable / disable feature modules")
    msp = mod.add_subparsers(dest="module_cmd", required=True)

    ml = msp.add_parser("list", help="List available modules")
    ml.set_defaults(handler=lambda a: _module_list(Store(a.db)))

    me = msp.add_parser("enable", help="Enable a module")
    me.add_argument("name")
    me.set_defaults(handler=lambda a: _module_set(Store(a.db), a.name, True))

    md = msp.add_parser("disable", help="Disable an optional module")
    md.add_argument("name")
    md.set_defaults(handler=lambda a: _module_set(Store(a.db), a.name, False))

    for module in get_registry().all():
        module.register_commands(sub, store_factory)

    return parser, db_box


def run(argv: list[str] | None = None) -> int:
    parser, db_box = build_parser()
    args = parser.parse_args(argv)
    db_box["db"] = args.db
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    try:
        return int(handler(args))
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> None:
    """Console-script entry point."""
    raise SystemExit(run(argv))


if __name__ == "__main__":
    main()
