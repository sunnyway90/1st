"""Tests for the LiteWork collaboration CLI."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from litework.cli import run
from litework.core.plugins import get_registry, reset_registry
from litework.core.store import Store


class LiteWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_registry()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.tmp.cleanup()
        reset_registry()

    def run_cli(self, *args: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run(["--db", self.db, *args])
        return code, buf.getvalue()

    def bootstrap_team(self) -> None:
        self.assertEqual(self.run_cli("org", "create", "Acme")[0], 0)
        self.assertEqual(
            self.run_cli("org", "add-user", "Acme", "Alice", "--role", "owner")[0],
            0,
        )
        self.assertEqual(self.run_cli("org", "add-user", "Acme", "Bob")[0], 0)
        self.assertEqual(self.run_cli("org", "login", "Acme", "Alice")[0], 0)

    def test_org_and_login(self) -> None:
        self.bootstrap_team()
        code, out = self.run_cli("org", "whoami")
        self.assertEqual(code, 0)
        self.assertIn("Alice @ Acme", out)
        code, out = self.run_cli("org", "people", "Acme")
        self.assertIn("Alice", out)
        self.assertIn("Bob", out)

    def test_company_cap_ten_people(self) -> None:
        self.run_cli("org", "create", "TinyCo")
        for i in range(10):
            code, _ = self.run_cli("org", "add-user", "TinyCo", f"User{i}")
            self.assertEqual(code, 0)
        code, out = self.run_cli("org", "add-user", "TinyCo", "Overflow")
        self.assertEqual(code, 1)
        self.assertIn("10 people", out)

    def test_schedule_offer_book_and_find(self) -> None:
        self.bootstrap_team()
        code, out = self.run_cli(
            "schedule",
            "offer",
            "2026-08-10T10:00",
            "2026-08-10T11:00",
            "--title",
            "Sync window",
        )
        self.assertEqual(code, 0)
        self.assertIn("offered free slot", out)
        slot_id = out.split()[3].rstrip(":")

        self.assertEqual(self.run_cli("org", "login", "Acme", "Bob")[0], 0)
        code, out = self.run_cli("schedule", "book", slot_id, "--note", "design review")
        self.assertEqual(code, 0)
        self.assertIn("booked", out)

        code, out = self.run_cli("schedule", "show", "--day", "2026-08-10")
        self.assertEqual(code, 0)
        self.assertIn("booked", out)
        self.assertIn("Alice", out)

        # Mutual free check with a conflict
        code, out = self.run_cli(
            "schedule",
            "find",
            "Alice",
            "Bob",
            "--start",
            "2026-08-10T10:00",
            "--end",
            "2026-08-10T11:00",
        )
        self.assertEqual(code, 1)
        self.assertIn("conflicts", out)

        # Clear window later in the day
        code, out = self.run_cli(
            "schedule",
            "find",
            "Alice",
            "Bob",
            "--start",
            "2026-08-10T14:00",
            "--end",
            "2026-08-10T15:00",
        )
        self.assertEqual(code, 0)
        self.assertIn("mutual free", out)

    def test_progress_feed(self) -> None:
        self.bootstrap_team()
        code, out = self.run_cli(
            "progress",
            "post",
            "Landing page",
            "--body",
            "Hero done",
            "--percent",
            "40",
            "--tag",
            "web",
        )
        self.assertEqual(code, 0)
        self.assertIn("40%", out)

        self.assertEqual(self.run_cli("org", "login", "Acme", "Bob")[0], 0)
        self.run_cli(
            "progress",
            "post",
            "API draft",
            "--percent",
            "20",
            "--tag",
            "backend",
        )
        code, out = self.run_cli("progress", "feed")
        self.assertEqual(code, 0)
        self.assertIn("Landing page", out)
        self.assertIn("API draft", out)
        self.assertIn("Alice", out)
        self.assertIn("Bob", out)

    def test_module_disable(self) -> None:
        self.bootstrap_team()
        code, out = self.run_cli("module", "disable", "progress")
        self.assertEqual(code, 0)
        self.assertIn("disabled", out)
        code, err_out = self.run_cli("progress", "feed")
        # RuntimeError goes to stderr; return code should be 1
        self.assertEqual(code, 1)

        code, out = self.run_cli("module", "enable", "progress")
        self.assertEqual(code, 0)
        code, out = self.run_cli("progress", "feed")
        self.assertEqual(code, 0)

        code, out = self.run_cli("module", "disable", "org")
        self.assertEqual(code, 1)
        self.assertIn("required", out)

    def test_builtin_modules_registered(self) -> None:
        names = get_registry().names()
        self.assertEqual(names, ["org", "progress", "schedule"])

    def test_store_cannot_book_own_slot(self) -> None:
        store = Store(self.db)
        c = store.create_company("Solo")
        u = store.create_user(c.id, "Ada", role="owner")
        slot = store.create_slot(
            c.id, u.id, "2026-08-11T09:00", "2026-08-11T10:00", "focus"
        )
        with self.assertRaises(ValueError):
            store.book_slot(slot.id, u.id)


if __name__ == "__main__":
    unittest.main()
