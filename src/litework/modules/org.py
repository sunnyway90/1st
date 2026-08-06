"""Company + people module (always on)."""

from __future__ import annotations

import argparse
from typing import Callable

from litework.core.plugins import Module
from litework.core.store import Store


def register_commands(
    subparsers: argparse._SubParsersAction, store_factory: Callable[[], Store]
) -> None:
    p = subparsers.add_parser("org", help="Manage companies and people")
    sp = p.add_subparsers(dest="org_cmd", required=True)

    c = sp.add_parser("create", help="Create a company")
    c.add_argument("name")
    c.set_defaults(handler=lambda a: _create_company(store_factory(), a))

    l = sp.add_parser("list", help="List companies")
    l.set_defaults(handler=lambda a: _list_companies(store_factory()))

    add = sp.add_parser("add-user", help="Add a person to a company")
    add.add_argument("company")
    add.add_argument("name")
    add.add_argument(
        "--role", choices=["owner", "admin", "member"], default="member"
    )
    add.set_defaults(handler=lambda a: _add_user(store_factory(), a))

    people = sp.add_parser("people", help="List people in a company")
    people.add_argument("company")
    people.set_defaults(handler=lambda a: _list_people(store_factory(), a))

    who = sp.add_parser("whoami", help="Show current user")
    who.set_defaults(handler=lambda a: _whoami(store_factory()))

    login = sp.add_parser("login", help="Set current user for this workspace")
    login.add_argument("company")
    login.add_argument("name")
    login.set_defaults(handler=lambda a: _login(store_factory(), a))


def _create_company(store: Store, args: argparse.Namespace) -> int:
    if store.get_company_by_name(args.name):
        print(f"error: company already exists: {args.name}")
        return 1
    company = store.create_company(args.name)
    print(f"created company {company.name} ({company.id})")
    return 0


def _list_companies(store: Store) -> int:
    companies = store.list_companies()
    if not companies:
        print("(no companies yet)")
        return 0
    for c in companies:
        print(f"{c.name}\t{c.id}\t{c.created_at}")
    return 0


def _resolve_company(store: Store, name_or_id: str):
    company = store.get_company(name_or_id) or store.get_company_by_name(name_or_id)
    if not company:
        raise ValueError(f"company not found: {name_or_id}")
    return company


def _add_user(store: Store, args: argparse.Namespace) -> int:
    company = _resolve_company(store, args.company)
    existing = store.list_users(company.id)
    if len(existing) >= 10:
        print("error: company already has 10 people (designed for small teams)")
        return 1
    if store.find_user(company.id, args.name):
        print(f"error: user already exists in {company.name}: {args.name}")
        return 1
    role = args.role
    if not existing:
        role = "owner"
    user = store.create_user(company.id, args.name, role=role)
    print(f"added {user.name} ({user.role}) to {company.name}")
    return 0


def _list_people(store: Store, args: argparse.Namespace) -> int:
    company = _resolve_company(store, args.company)
    people = store.list_users(company.id)
    if not people:
        print(f"(no people in {company.name})")
        return 0
    for u in people:
        print(f"{u.name}\t{u.role}\t{u.id}")
    return 0


def _whoami(store: Store) -> int:
    user = store.get_current_user()
    if not user:
        print("not logged in — run: litework org login <company> <name>")
        return 1
    company = store.get_company(user.company_id)
    cname = company.name if company else user.company_id
    print(f"{user.name} @ {cname} ({user.role})")
    return 0


def _login(store: Store, args: argparse.Namespace) -> int:
    company = _resolve_company(store, args.company)
    user = store.find_user(company.id, args.name)
    if not user:
        print(f"error: user not found: {args.name} in {company.name}")
        return 1
    store.set_current_user(user.id)
    print(f"logged in as {user.name} @ {company.name}")
    return 0


MODULE = Module(
    name="org",
    description="Companies and people (core)",
    register_commands=register_commands,
    required=True,
)
