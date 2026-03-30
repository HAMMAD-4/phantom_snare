"""MySQL persistence layer for phantom_snare.

This module manages a single MySQL connection per :class:`DatabaseManager`
instance and provides a clean API for bootstrapping the schema and persisting
:class:`~phantom_snare.logger.CaptureRecord` objects.

Typical usage::

    from phantom_snare.config import Config
    from phantom_snare.database import DatabaseManager

    cfg = Config(db_enabled=True, db_host="localhost", db_user="root",
                 db_password="", db_name="phantom_snare")
    with DatabaseManager(cfg) as db:
        db.save_capture(record)
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .config import Config
    from .logger import CaptureRecord

_module_logger = logging.getLogger("phantom_snare.database")


def _get_connector():
    """Import and return the ``mysql.connector`` module.

    Factored out so that tests can patch ``phantom_snare.database._get_connector``
    without touching ``sys.modules`` internals.

    Raises:
        RuntimeError: If ``mysql-connector-python`` is not installed.
    """
    try:
        import mysql.connector  # type: ignore[import-untyped]

        return mysql.connector
    except ImportError as exc:
        raise RuntimeError(
            "mysql-connector-python is required for database support. "
            "Install it with: pip install mysql-connector-python>=9.3"
        ) from exc

# DDL executed once on first connect to ensure the table exists.
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS captures (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    timestamp    DATETIME(6)  NOT NULL COMMENT 'UTC time of the connection',
    remote_ip    VARCHAR(45)  NOT NULL COMMENT 'Source IP (supports IPv6)',
    remote_port  SMALLINT UNSIGNED NOT NULL,
    local_port   SMALLINT UNSIGNED NOT NULL,
    payload_bytes INT UNSIGNED NOT NULL,
    payload      MEDIUMTEXT   DEFAULT NULL COMMENT 'UTF-8 decoded payload',
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_remote_ip (remote_ip),
    INDEX idx_local_port (local_port),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

_INSERT_SQL = """
INSERT INTO captures
    (timestamp, remote_ip, remote_port, local_port, payload_bytes, payload)
VALUES
    (%(timestamp)s, %(remote_ip)s, %(remote_port)s,
     %(local_port)s, %(payload_bytes)s, %(payload)s)
"""


class DatabaseManager:
    """Manages the MySQL connection and capture persistence.

    Can be used as a context manager (``with`` statement) for automatic
    connection cleanup, or managed manually via :meth:`connect` /
    :meth:`close`.

    Args:
        config: Runtime configuration containing MySQL credentials.
    """

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._connection = None  # type: Optional[object]

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "DatabaseManager":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the MySQL connection and bootstrap the schema.

        Raises:
            RuntimeError: If ``mysql-connector-python`` is not installed.
            mysql.connector.Error: On connection failure.
        """
        connector = _get_connector()

        self._connection = connector.connect(
            host=self._config.db_host,
            port=self._config.db_port,
            user=self._config.db_user,
            password=self._config.db_password,
            database=self._config.db_name,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=True,
            connection_timeout=10,
        )
        self._bootstrap_schema()
        _module_logger.info(
            "Connected to MySQL database '%s' on %s:%d",
            self._config.db_name,
            self._config.db_host,
            self._config.db_port,
        )

    def close(self) -> None:
        """Close the MySQL connection if it is open."""
        if self._connection is not None:
            try:
                self._connection.close()  # type: ignore[union-attr]
            except Exception:  # pylint: disable=broad-except
                pass
            finally:
                self._connection = None
                _module_logger.debug("MySQL connection closed.")

    @property
    def is_connected(self) -> bool:
        """Return *True* if the connection is open and alive."""
        if self._connection is None:
            return False
        try:
            return self._connection.is_connected()  # type: ignore[union-attr]
        except Exception:  # pylint: disable=broad-except
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_capture(self, record: "CaptureRecord") -> None:
        """Persist a single capture record to the ``captures`` table.

        If the connection has been lost, a reconnect is attempted
        automatically before inserting.

        Args:
            record: The capture event to persist.
        """
        if not self.is_connected:
            _module_logger.warning("MySQL connection lost – reconnecting…")
            self.connect()

        params = {
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "remote_ip": record.remote_ip,
            "remote_port": record.remote_port,
            "local_port": record.local_port,
            "payload_bytes": len(record.payload),
            "payload": record.payload_text(),
        }

        try:
            cursor = self._connection.cursor()  # type: ignore[union-attr]
            cursor.execute(_INSERT_SQL, params)
            cursor.close()
        except Exception as exc:  # pylint: disable=broad-except
            _module_logger.error("Failed to save capture to MySQL: %s", exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _bootstrap_schema(self) -> None:
        """Create the ``captures`` table if it does not already exist."""
        try:
            cursor = self._connection.cursor()  # type: ignore[union-attr]
            cursor.execute(_CREATE_TABLE_SQL)
            cursor.close()
            _module_logger.debug("Schema bootstrap complete.")
        except Exception as exc:  # pylint: disable=broad-except
            _module_logger.error("Failed to bootstrap database schema: %s", exc)
