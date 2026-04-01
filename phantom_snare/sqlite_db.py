import logging
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional

_module_logger = logging.getLogger("phantom_snare.sqlite_db")

_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS captures (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp     TEXT    NOT NULL,
        remote_ip     TEXT    NOT NULL,
        remote_port   INTEGER NOT NULL,
        local_port    INTEGER NOT NULL,
        payload_bytes INTEGER NOT NULL,
        payload       TEXT,
        created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cap_remote_ip  ON captures (remote_ip)",
    "CREATE INDEX IF NOT EXISTS idx_cap_local_port ON captures (local_port)",
    "CREATE INDEX IF NOT EXISTS idx_cap_timestamp  ON captures (timestamp)",
    """
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT NOT NULL,
        event_type  TEXT NOT NULL,
        remote_ip   TEXT NOT NULL,
        details     TEXT,
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_evt_remote_ip  ON events (remote_ip)",
    "CREATE INDEX IF NOT EXISTS idx_evt_event_type ON events (event_type)",
    """
    CREATE TABLE IF NOT EXISTS blocked_ips (
        ip         TEXT PRIMARY KEY,
        reason     TEXT,
        blocked_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS honey_tokens (
        token_id    TEXT PRIMARY KEY,
        path        TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS honey_token_hits (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        token_id  TEXT NOT NULL,
        remote_ip TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        details   TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_hth_token_id  ON honey_token_hits (token_id)",
    "CREATE INDEX IF NOT EXISTS idx_hth_remote_ip ON honey_token_hits (remote_ip)",
    """
    CREATE TABLE IF NOT EXISTS site_visits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT NOT NULL,
        remote_ip   TEXT NOT NULL,
        host        TEXT,
        path        TEXT,
        method      TEXT,
        is_harmful  INTEGER NOT NULL DEFAULT 0,
        harm_reason TEXT,
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sv_remote_ip  ON site_visits (remote_ip)",
    "CREATE INDEX IF NOT EXISTS idx_sv_is_harmful ON site_visits (is_harmful)",
]


class EvidenceStore:
    def __init__(self, db_path: str = "phantom_snare_evidence.db") -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._bootstrap()
        _module_logger.info("[EvidenceStore] Connected to %s", self._db_path)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None

    def __enter__(self) -> "EvidenceStore":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _bootstrap(self) -> None:
        with self._lock:
            for stmt in _DDL_STATEMENTS:
                self._conn.execute(stmt)  # type: ignore[union-attr]
            self._conn.commit()  # type: ignore[union-attr]
        _module_logger.debug("[EvidenceStore] Schema bootstrap complete.")

    def is_connected(self) -> bool:
        return self._conn is not None

    def save_capture(self, record: object) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT INTO captures
                           (timestamp, remote_ip, remote_port, local_port,
                            payload_bytes, payload)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        record.timestamp.isoformat(),  # type: ignore[attr-defined]
                        record.remote_ip,  # type: ignore[attr-defined]
                        record.remote_port,  # type: ignore[attr-defined]
                        record.local_port,  # type: ignore[attr-defined]
                        len(record.payload),  # type: ignore[attr-defined]
                        record.payload_text(),  # type: ignore[attr-defined]
                    ),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] save_capture failed: %s", exc)

    def get_recent_captures(self, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                """SELECT id, timestamp, remote_ip, remote_port, local_port,
                          payload_bytes, payload
                   FROM captures
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_ip_stats(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                """SELECT remote_ip,
                          COUNT(*)          AS total_connections,
                          SUM(payload_bytes) AS total_bytes,
                          MAX(timestamp)    AS last_seen
                   FROM captures
                   GROUP BY remote_ip
                   ORDER BY total_connections DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def save_event(
        self, event_type: str, remote_ip: str, details: str = ""
    ) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT INTO events (timestamp, event_type, remote_ip, details)
                       VALUES (?, ?, ?, ?)""",
                    (
                        datetime.now(tz=timezone.utc).isoformat(),
                        event_type,
                        remote_ip,
                        details,
                    ),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] save_event failed: %s", exc)

    def get_recent_events(self, limit: int = 100) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def block_ip(self, ip: str, reason: str = "") -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT OR REPLACE INTO blocked_ips (ip, reason, blocked_at)
                       VALUES (?, ?, ?)""",
                    (ip, reason, datetime.now(tz=timezone.utc).isoformat()),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] block_ip failed: %s", exc)

    def unblock_ip(self, ip: str) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    "DELETE FROM blocked_ips WHERE ip = ?", (ip,)
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] unblock_ip failed: %s", exc)

    def is_blocked(self, ip: str) -> bool:
        with self._lock:
            row = self._conn.execute(  # type: ignore[union-attr]
                "SELECT ip FROM blocked_ips WHERE ip = ?", (ip,)
            ).fetchone()
        return row is not None

    def get_blocked_ips(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                "SELECT ip, reason, blocked_at FROM blocked_ips ORDER BY blocked_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def register_honey_token(
        self, token_id: str, path: str, description: str = ""
    ) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT OR IGNORE INTO honey_tokens (token_id, path, description)
                       VALUES (?, ?, ?)""",
                    (token_id, path, description),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] register_honey_token failed: %s", exc)

    def record_honey_token_hit(
        self, token_id: str, remote_ip: str, details: str = ""
    ) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT INTO honey_token_hits (token_id, remote_ip, timestamp, details)
                       VALUES (?, ?, ?, ?)""",
                    (
                        token_id,
                        remote_ip,
                        datetime.now(tz=timezone.utc).isoformat(),
                        details,
                    ),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error(
                    "[EvidenceStore] record_honey_token_hit failed: %s", exc
                )

    def get_honey_token_hits(self, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                """SELECT h.id, h.token_id, h.remote_ip, h.timestamp, h.details,
                          t.path, t.description
                   FROM honey_token_hits h
                   LEFT JOIN honey_tokens t ON h.token_id = t.token_id
                   ORDER BY h.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_honey_token_hit_count(self) -> int:
        with self._lock:
            row = self._conn.execute(  # type: ignore[union-attr]
                "SELECT COUNT(*) FROM honey_token_hits"
            ).fetchone()
        return row[0] if row else 0

    def save_site_visit(
        self,
        remote_ip: str,
        host: str,
        path: str,
        method: str,
        is_harmful: bool,
        harm_reason: str = "",
    ) -> None:
        with self._lock:
            try:
                self._conn.execute(  # type: ignore[union-attr]
                    """INSERT INTO site_visits
                           (timestamp, remote_ip, host, path, method, is_harmful, harm_reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now(tz=timezone.utc).isoformat(),
                        remote_ip,
                        host,
                        path,
                        method,
                        1 if is_harmful else 0,
                        harm_reason,
                    ),
                )
                self._conn.commit()  # type: ignore[union-attr]
            except Exception as exc:
                _module_logger.error("[EvidenceStore] save_site_visit failed: %s", exc)

    def get_recent_site_visits(self, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(  # type: ignore[union-attr]
                """SELECT id, timestamp, remote_ip, host, path, method,
                          is_harmful, harm_reason
                   FROM site_visits
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
