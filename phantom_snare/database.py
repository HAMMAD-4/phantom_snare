import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .config import Config
    from .logger import CaptureRecord

_module_logger = logging.getLogger("phantom_snare.database")


def _get_connector():
    try:
        import mysql.connector  # type: ignore[import-untyped]
        return mysql.connector
    except ImportError as exc:
        raise RuntimeError(
            "mysql-connector-python is required for database support. "
            "Install it with: pip install mysql-connector-python>=9.3"
        ) from exc


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS captures (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    timestamp    DATETIME(6)  NOT NULL,
    remote_ip    VARCHAR(45)  NOT NULL,
    remote_port  SMALLINT UNSIGNED NOT NULL,
    local_port   SMALLINT UNSIGNED NOT NULL,
    payload_bytes INT UNSIGNED NOT NULL,
    payload      MEDIUMTEXT   DEFAULT NULL,
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
    def __init__(self, config: "Config") -> None:
        self._config = config
        self._connection = None  # type: Optional[object]

    def __enter__(self) -> "DatabaseManager":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def connect(self) -> None:
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
        if self._connection is not None:
            try:
                self._connection.close()  # type: ignore[union-attr]
            except Exception:
                pass
            finally:
                self._connection = None

    @property
    def is_connected(self) -> bool:
        if self._connection is None:
            return False
        try:
            return self._connection.is_connected()  # type: ignore[union-attr]
        except Exception:
            return False

    def save_capture(self, record: "CaptureRecord") -> None:
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
        except Exception as exc:
            _module_logger.error("Failed to save capture to MySQL: %s", exc)

    def _bootstrap_schema(self) -> None:
        try:
            cursor = self._connection.cursor()  # type: ignore[union-attr]
            cursor.execute(_CREATE_TABLE_SQL)
            cursor.close()
        except Exception as exc:
            _module_logger.error("Failed to bootstrap database schema: %s", exc)
