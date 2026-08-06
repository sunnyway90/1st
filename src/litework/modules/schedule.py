"""Schedule module — publish free time and book each other."""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import Callable

from litework.core.plugins import Module, ensure_module_enabled
from litework.core.store import Store


def _parse_dt(value: str) -> str:
    """Normalize to YYYY-MM-DDTHH:MM."""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            continue
    raise ValueError(
        f"invalid datetime '{value}', use YYYY-MM-DDTHH:MM"
    )


def register_commands(
    subparsers: argparse._SubParsersAction, store_factory: Callable[[], Store]
) -> None:
    p = subparsers.add_parser(
        "schedule", help="Share free time and book teammates"
    )
    sp = p.add_subparsers(dest="schedule_cmd", required=True)

    offer = sp.add_parser("offer", help="Publish a free work slot")
    offer.add_argument("start", help="YYYY-MM-DDTHH:MM")
    offer.add_argument("end", help="YYYY-MM-DDTHH:MM")
    offer.add_argument("--title", default="Open for collaboration")
    offer.add_argument("--note", default="")
    offer.set_defaults(handler=lambda a: _offer(store_factory(), a))

    busy = sp.add_parser("busy", help="Mark yourself busy")
    busy.add_argument("start")
    busy.add_argument("end")
    busy.add_argument("--title", default="Busy")
    busy.add_argument("--note", default="")
    busy.set_defaults(handler=lambda a: _busy(store_factory(), a))

    book = sp.add_parser("book", help="Book a teammate's free slot")
    book.add_argument("slot_id")
    book.add_argument("--note", default="")
    book.set_defaults(handler=lambda a: _book(store_factory(), a))

    release = sp.add_parser("release", help="Release a booked slot back to free")
    release.add_argument("slot_id")
    release.set_defaults(handler=lambda a: _release(store_factory(), a))

    show = sp.add_parser("show", help="Show schedule for a person or day")
    show.add_argument("--person", default=None, help="Teammate name")
    show.add_argument("--day", default=None, help="YYYY-MM-DD")
    show.set_defaults(handler=lambda a: _show(store_factory(), a))

    find = sp.add_parser(
        "find", help="Find mutual free windows among teammates"
    )
    find.add_argument("people", nargs="+", help="Names including yourself")
    find.add_argument("--start", required=True)
    find.add_argument("--end", required=True)
    find.set_defaults(handler=lambda a: _find(store_factory(), a))


def _require_user(store: Store):
    ensure_module_enabled(store, "schedule")
    user = store.get_current_user()
    if not user:
        raise RuntimeError("login first: litework org login <company> <name>")
    return user


def _offer(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    start, end = _parse_dt(args.start), _parse_dt(args.end)
    slot = store.create_slot(
        user.company_id,
        user.id,
        start,
        end,
        title=args.title,
        status="free",
        note=args.note,
    )
    print(f"offered free slot {slot.id}: {slot.start_at} → {slot.end_at}")
    return 0


def _busy(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    start, end = _parse_dt(args.start), _parse_dt(args.end)
    slot = store.create_slot(
        user.company_id,
        user.id,
        start,
        end,
        title=args.title,
        status="busy",
        note=args.note,
    )
    print(f"marked busy {slot.id}: {slot.start_at} → {slot.end_at}")
    return 0


def _book(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    slot = store.book_slot(args.slot_id, user.id, note=args.note)
    owner = store.get_user(slot.owner_id)
    oname = owner.name if owner else slot.owner_id
    print(
        f"booked {slot.id} with {oname}: {slot.start_at} → {slot.end_at}"
        + (f" ({slot.note})" if slot.note else "")
    )
    return 0


def _release(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    slot = store.get_slot(args.slot_id)
    if not slot:
        print(f"error: slot not found: {args.slot_id}")
        return 1
    if slot.owner_id != user.id and slot.booker_id != user.id:
        print("error: only owner or booker can release this slot")
        return 1
    released = store.release_slot(args.slot_id)
    print(f"released {released.id} back to free")
    return 0


def _show(store: Store, args: argparse.Namespace) -> int:
    user = _require_user(store)
    owner_id = None
    if args.person:
        person = store.find_user(user.company_id, args.person)
        if not person:
            print(f"error: person not found: {args.person}")
            return 1
        owner_id = person.id
    slots = store.list_slots(user.company_id, owner_id=owner_id, day=args.day)
    if not slots:
        print("(no slots)")
        return 0
    users = {u.id: u.name for u in store.list_users(user.company_id)}
    for s in slots:
        owner = users.get(s.owner_id, s.owner_id)
        booker = users.get(s.booker_id, "-") if s.booker_id else "-"
        print(
            f"{s.id}\t{s.start_at}→{s.end_at}\t{s.status}\t"
            f"owner={owner}\tbooker={booker}\t{s.title}"
        )
    return 0


def _find(store: Store, args: argparse.Namespace) -> int:
    """Heuristic: window is mutual-free if nobody is busy/booked then."""
    user = _require_user(store)
    start, end = _parse_dt(args.start), _parse_dt(args.end)
    ids: list[str] = []
    for name in args.people:
        person = store.find_user(user.company_id, name)
        if not person:
            print(f"error: person not found: {name}")
            return 1
        ids.append(person.id)
    conflicts = store.overlapping_slots(user.company_id, ids, start, end)
    if conflicts:
        print("conflicts found — not fully free:")
        users = {u.id: u.name for u in store.list_users(user.company_id)}
        for s in conflicts:
            print(
                f"  {users.get(s.owner_id, s.owner_id)} "
                f"{s.start_at}→{s.end_at} [{s.status}] {s.title}"
            )
        return 1
    print(f"mutual free: {start} → {end} for {', '.join(args.people)}")
    return 0


MODULE = Module(
    name="schedule",
    description="Offer free time and book teammates",
    register_commands=register_commands,
)
