"""Progress module — share what you are working on."""

from __future__ import annotations

import argparse
from typing import Callable

from litework.core.plugins import Module, ensure_module_enabled
from litework.core.store import Store


def register_commands(
    subparsers: argparse._SubParsersAction, store_factory: Callable[[], Store]
) -> None:
    p = subparsers.add_parser("progress", help="Share and view work progress")
    sp = p.add_subparsers(dest="progress_cmd", required=True)

    post = sp.add_parser("post", help="Post a progress update")
    post.add_argument("title")
    post.add_argument("--body", default="")
    post.add_argument("--percent", type=int, default=0)
    post.add_argument(
        "--tag", action="append", default=[], help="Repeatable tag"
    )
    post.set_defaults(handler=lambda a: _post(store_factory(), a))

    feed = sp.add_parser("feed", help="Team progress feed")
    feed.add_argument("--person", default=None)
    feed.add_argument("--limit", type=int, default=20)
    feed.set_defaults(handler=lambda a: _feed(store_factory(), a))

    mine = sp.add_parser("mine", help="Your recent updates")
    mine.add_argument("--limit", type=int, default=20)
    mine.set_defaults(handler=lambda a: _mine(store_factory(), a))


def _require_user(store: Store):
    ensure_module_enabled(store, "progress")
    user = store.get_current_user()
    if not user:
        raise RuntimeError("login first: litework org login <company> <name>")
    return user


def _post(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    update = store.add_progress(
        user.company_id,
        user.id,
        title=args.title,
        body=args.body,
        percent=args.percent,
        tags=args.tag,
    )
    tags = f" [{', '.join(update.tags)}]" if update.tags else ""
    print(
        f"posted {update.id}: {update.percent}% — {update.title}{tags}"
    )
    return 0


def _feed(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    author_id = None
    if args.person:
        person = store.find_user(user.company_id, args.person)
        if not person:
            print(f"error: person not found: {args.person}")
            return 1
        author_id = person.id
    updates = store.list_progress(
        user.company_id, author_id=author_id, limit=args.limit
    )
    if not updates:
        print("(no progress yet)")
        return 0
    names = {u.id: u.name for u in store.list_users(user.company_id)}
    for u in updates:
        tags = f" #{' #'.join(u.tags)}" if u.tags else ""
        author = names.get(u.author_id, u.author_id)
        body = f" — {u.body}" if u.body else ""
        print(
            f"{u.created_at}\t{author}\t{u.percent}%\t{u.title}{body}{tags}"
        )
    return 0


def _mine(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    args.person = user.name
    return _feed(store, args)


MODULE = Module(
    name="progress",
    description="Share work progress with the team",
    register_commands=register_commands,
)
