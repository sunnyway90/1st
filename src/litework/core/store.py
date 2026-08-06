"""SQLite-backed store sized for ~10 companies × ~10 people."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from litework.core.models import Company, ModuleState, ProgressUpdate, TimeSlot, User

DEFAULT_DB = Path.home() / ".litework" / "litework.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str = "") -> str:
    token = uuid.uuid4().hex[:10]
    return f"{prefix}{token}" if prefix else token


class Store:
    """Tiny persistence layer; one file, no server required."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    created_at TEXT NOT NULL,
                    UNIQUE(company_id, name),
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS time_slots (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    start_at TEXT NOT NULL,
                    end_at TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'free',
                    booker_id TEXT,
                    note TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(booker_id) REFERENCES users(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS progress_updates (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    percent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS modules (
                    name TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    config_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    # ---- meta / session ----

    def set_meta(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_current_user(self, user_id: str) -> None:
        self.set_meta("current_user_id", user_id)

    def get_current_user(self) -> User | None:
        uid = self.get_meta("current_user_id")
        return self.get_user(uid) if uid else None

    # ---- companies ----

    def create_company(self, name: str) -> Company:
        company = Company(id=new_id("c_"), name=name.strip(), created_at=utc_now())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO companies(id, name, created_at) VALUES(?,?,?)",
                (company.id, company.name, company.created_at),
            )
        return company

    def list_companies(self) -> list[Company]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, name, created_at FROM companies ORDER BY name"
            ).fetchall()
        return [Company(**dict(r)) for r in rows]

    def get_company(self, company_id: str) -> Company | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, name, created_at FROM companies WHERE id = ?",
                (company_id,),
            ).fetchone()
        return Company(**dict(row)) if row else None

    def get_company_by_name(self, name: str) -> Company | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, name, created_at FROM companies WHERE name = ?",
                (name.strip(),),
            ).fetchone()
        return Company(**dict(row)) if row else None

    # ---- users ----

    def create_user(
        self, company_id: str, name: str, role: str = "member"
    ) -> User:
        if role not in {"owner", "admin", "member"}:
            raise ValueError(f"invalid role: {role}")
        user = User(
            id=new_id("u_"),
            company_id=company_id,
            name=name.strip(),
            role=role,
            created_at=utc_now(),
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO users(id, company_id, name, role, created_at) "
                "VALUES(?,?,?,?,?)",
                (user.id, user.company_id, user.name, user.role, user.created_at),
            )
        return user

    def list_users(self, company_id: str) -> list[User]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, company_id, name, role, created_at FROM users "
                "WHERE company_id = ? ORDER BY name",
                (company_id,),
            ).fetchall()
        return [User(**dict(r)) for r in rows]

    def get_user(self, user_id: str) -> User | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, company_id, name, role, created_at FROM users "
                "WHERE id = ?",
                (user_id,),
            ).fetchone()
        return User(**dict(row)) if row else None

    def find_user(self, company_id: str, name: str) -> User | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, company_id, name, role, created_at FROM users "
                "WHERE company_id = ? AND name = ?",
                (company_id, name.strip()),
            ).fetchone()
        return User(**dict(row)) if row else None

    # ---- schedule ----

    def create_slot(
        self,
        company_id: str,
        owner_id: str,
        start_at: str,
        end_at: str,
        title: str,
        status: str = "free",
        note: str = "",
    ) -> TimeSlot:
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")
        slot = TimeSlot(
            id=new_id("s_"),
            company_id=company_id,
            owner_id=owner_id,
            start_at=start_at,
            end_at=end_at,
            title=title.strip(),
            status=status,
            note=note,
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO time_slots"
                "(id, company_id, owner_id, start_at, end_at, title, status, note) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    slot.id,
                    slot.company_id,
                    slot.owner_id,
                    slot.start_at,
                    slot.end_at,
                    slot.title,
                    slot.status,
                    slot.note,
                ),
            )
        return slot

    def list_slots(
        self,
        company_id: str,
        owner_id: str | None = None,
        day: str | None = None,
    ) -> list[TimeSlot]:
        sql = (
            "SELECT id, company_id, owner_id, start_at, end_at, title, status, "
            "booker_id, note FROM time_slots WHERE company_id = ?"
        )
        params: list[Any] = [company_id]
        if owner_id:
            sql += " AND owner_id = ?"
            params.append(owner_id)
        if day:
            sql += " AND start_at LIKE ?"
            params.append(f"{day}%")
        sql += " ORDER BY start_at"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [TimeSlot(**dict(r)) for r in rows]

    def get_slot(self, slot_id: str) -> TimeSlot | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, company_id, owner_id, start_at, end_at, title, status, "
                "booker_id, note FROM time_slots WHERE id = ?",
                (slot_id,),
            ).fetchone()
        return TimeSlot(**dict(row)) if row else None

    def book_slot(self, slot_id: str, booker_id: str, note: str = "") -> TimeSlot:
        slot = self.get_slot(slot_id)
        if not slot:
            raise ValueError(f"slot not found: {slot_id}")
        if slot.status != "free":
            raise ValueError(f"slot is not free (status={slot.status})")
        if slot.owner_id == booker_id:
            raise ValueError("cannot book your own free slot; mark it busy instead")
        booker = self.get_user(booker_id)
        if not booker or booker.company_id != slot.company_id:
            raise ValueError("booker must belong to the same company")
        with self._conn() as conn:
            conn.execute(
                "UPDATE time_slots SET status='booked', booker_id=?, note=? "
                "WHERE id=?",
                (booker_id, note or slot.note, slot_id),
            )
        updated = self.get_slot(slot_id)
        assert updated is not None
        return updated

    def release_slot(self, slot_id: str) -> TimeSlot:
        slot = self.get_slot(slot_id)
        if not slot:
            raise ValueError(f"slot not found: {slot_id}")
        with self._conn() as conn:
            conn.execute(
                "UPDATE time_slots SET status='free', booker_id=NULL WHERE id=?",
                (slot_id,),
            )
        updated = self.get_slot(slot_id)
        assert updated is not None
        return updated

    def overlapping_slots(
        self, company_id: str, user_ids: list[str], start_at: str, end_at: str
    ) -> list[TimeSlot]:
        """Return busy/booked slots that overlap the window for given users."""
        if not user_ids:
            return []
        placeholders = ",".join("?" for _ in user_ids)
        sql = f"""
            SELECT id, company_id, owner_id, start_at, end_at, title, status,
                   booker_id, note
            FROM time_slots
            WHERE company_id = ?
              AND owner_id IN ({placeholders})
              AND status IN ('booked', 'busy')
              AND start_at < ? AND end_at > ?
            ORDER BY start_at
        """
        params: list[Any] = [company_id, *user_ids, end_at, start_at]
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [TimeSlot(**dict(r)) for r in rows]

    # ---- progress ----

    def add_progress(
        self,
        company_id: str,
        author_id: str,
        title: str,
        body: str,
        percent: int = 0,
        tags: list[str] | None = None,
    ) -> ProgressUpdate:
        if not 0 <= percent <= 100:
            raise ValueError("percent must be between 0 and 100")
        update = ProgressUpdate(
            id=new_id("p_"),
            company_id=company_id,
            author_id=author_id,
            title=title.strip(),
            body=body.strip(),
            percent=percent,
            created_at=utc_now(),
            tags=tags or [],
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO progress_updates"
                "(id, company_id, author_id, title, body, percent, created_at, tags_json) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    update.id,
                    update.company_id,
                    update.author_id,
                    update.title,
                    update.body,
                    update.percent,
                    update.created_at,
                    json.dumps(update.tags),
                ),
            )
        return update

    def list_progress(
        self,
        company_id: str,
        author_id: str | None = None,
        limit: int = 50,
    ) -> list[ProgressUpdate]:
        sql = (
            "SELECT id, company_id, author_id, title, body, percent, created_at, "
            "tags_json FROM progress_updates WHERE company_id = ?"
        )
        params: list[Any] = [company_id]
        if author_id:
            sql += " AND author_id = ?"
            params.append(author_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        result: list[ProgressUpdate] = []
        for row in rows:
            data = dict(row)
            tags = json.loads(data.pop("tags_json") or "[]")
            result.append(ProgressUpdate(tags=tags, **data))
        return result

    # ---- modules ----

    def set_module(self, name: str, enabled: bool, config: dict | None = None) -> ModuleState:
        cfg = config or {}
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO modules(name, enabled, config_json) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET enabled=excluded.enabled, "
                "config_json=CASE WHEN excluded.config_json='{}' "
                "THEN modules.config_json ELSE excluded.config_json END",
                (name, 1 if enabled else 0, json.dumps(cfg)),
            )
        return self.get_module(name)  # type: ignore[return-value]

    def get_module(self, name: str) -> ModuleState | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT name, enabled, config_json FROM modules WHERE name = ?",
                (name,),
            ).fetchone()
        if not row:
            return None
        return ModuleState(
            name=row["name"],
            enabled=bool(row["enabled"]),
            config=json.loads(row["config_json"] or "{}"),
        )

    def list_modules(self) -> list[ModuleState]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT name, enabled, config_json FROM modules ORDER BY name"
            ).fetchall()
        return [
            ModuleState(
                name=r["name"],
                enabled=bool(r["enabled"]),
                config=json.loads(r["config_json"] or "{}"),
            )
            for r in rows
        ]

    def is_module_enabled(self, name: str, default: bool = True) -> bool:
        state = self.get_module(name)
        if state is None:
            return default
        return state.enabled
