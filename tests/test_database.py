"""Tests for phantom_snare.database (MySQL layer).

All tests use unittest.mock so no real MySQL server is required.
The key seam is ``phantom_snare.database._get_connector``, which is patched
to return a mock connector instead of the real ``mysql.connector`` module.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from phantom_snare.config import Config
from phantom_snare.database import DatabaseManager, _INSERT_SQL
from phantom_snare.logger import CaptureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(payload: bytes = b"GET / HTTP/1.0\r\n") -> CaptureRecord:
    return CaptureRecord(
        remote_ip="10.0.0.1",
        remote_port=54321,
        local_port=8080,
        payload=payload,
        timestamp=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def _db_config(**overrides) -> Config:
    defaults = dict(
        db_enabled=True,
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password="secret",
        db_name="phantom_snare",
    )
    defaults.update(overrides)
    return Config(**defaults)


def _make_mock_connector():
    """Return (mock_connector_module, mock_connection, mock_cursor)."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.is_connected.return_value = True

    mock_connector = MagicMock()
    mock_connector.connect.return_value = mock_conn
    return mock_connector, mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------

class TestConnect:
    def test_connect_calls_mysql_connector(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()

        mock_connector.connect.assert_called_once()
        call_kwargs = mock_connector.connect.call_args.kwargs
        assert call_kwargs["host"] == "localhost"
        assert call_kwargs["port"] == 3306
        assert call_kwargs["user"] == "root"
        assert call_kwargs["password"] == "secret"
        assert call_kwargs["database"] == "phantom_snare"

    def test_connect_bootstraps_schema(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()

        # _bootstrap_schema executes exactly one statement (CREATE TABLE …)
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args.args[0]
        assert "CREATE TABLE IF NOT EXISTS captures" in sql

    def test_connect_raises_if_connector_missing(self):
        with patch(
            "phantom_snare.database._get_connector",
            side_effect=RuntimeError("mysql-connector-python is required"),
        ):
            db = DatabaseManager(_db_config())
            with pytest.raises(RuntimeError, match="mysql-connector-python"):
                db.connect()

    def test_is_connected_true_after_connect(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
        assert db.is_connected

    def test_is_connected_false_before_connect(self):
        db = DatabaseManager(_db_config())
        assert not db.is_connected


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_calls_connection_close(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            db.close()

        mock_conn.close.assert_called_once()

    def test_close_without_connect_is_safe(self):
        db = DatabaseManager(_db_config())
        db.close()  # Should not raise

    def test_is_connected_false_after_close(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            db.close()
        assert not db.is_connected


# ---------------------------------------------------------------------------
# save_capture()
# ---------------------------------------------------------------------------

class TestSaveCapture:
    def test_save_capture_executes_insert(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            mock_cursor.reset_mock()
            db.save_capture(_make_record())

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args.args
        assert sql == _INSERT_SQL
        assert params["remote_ip"] == "10.0.0.1"
        assert params["remote_port"] == 54321
        assert params["local_port"] == 8080

    def test_save_capture_payload_bytes_count(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        payload = b"hello world"
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            mock_cursor.reset_mock()
            db.save_capture(_make_record(payload=payload))

        _, params = mock_cursor.execute.call_args.args
        assert params["payload_bytes"] == len(payload)
        assert params["payload"] == "hello world"

    def test_save_capture_timestamp_format(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            mock_cursor.reset_mock()
            db.save_capture(_make_record())

        _, params = mock_cursor.execute.call_args.args
        assert params["timestamp"] == "2025-06-01 12:00:00.000000"

    def test_save_capture_reconnects_on_lost_connection(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            # Simulate a dropped connection
            mock_conn.is_connected.return_value = False
            db.save_capture(_make_record())

        # connect() should have been called twice: initial + reconnect
        assert mock_connector.connect.call_count == 2

    def test_save_capture_db_error_is_logged_not_raised(self):
        mock_connector, mock_conn, mock_cursor = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            db = DatabaseManager(_db_config())
            db.connect()
            mock_cursor.reset_mock()
            mock_cursor.execute.side_effect = Exception("DB error")
            # Must not raise
            db.save_capture(_make_record())


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_connects_and_closes(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            with DatabaseManager(_db_config()) as db:
                assert db.is_connected
        assert not db.is_connected

    def test_context_manager_closes_on_exception(self):
        mock_connector, mock_conn, _ = _make_mock_connector()
        with patch("phantom_snare.database._get_connector", return_value=mock_connector):
            try:
                with DatabaseManager(_db_config()) as db:
                    raise ValueError("test error")
            except ValueError:
                pass
        assert not db.is_connected
