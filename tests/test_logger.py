"""Tests for phantom_snare.logger."""

import logging
from datetime import datetime, timezone

from phantom_snare.logger import CaptureRecord, build_logger, log_capture


class TestCaptureRecord:
    def _make_record(self, payload=b"GET / HTTP/1.0\r\n"):
        return CaptureRecord(
            remote_ip="192.168.1.50",
            remote_port=54321,
            local_port=8080,
            payload=payload,
        )

    def test_to_dict_keys(self):
        record = self._make_record()
        d = record.to_dict()
        assert set(d.keys()) == {
            "timestamp",
            "remote_ip",
            "remote_port",
            "local_port",
            "payload_bytes",
            "payload",
        }

    def test_to_dict_values(self):
        record = self._make_record(payload=b"hello")
        d = record.to_dict()
        assert d["remote_ip"] == "192.168.1.50"
        assert d["remote_port"] == 54321
        assert d["local_port"] == 8080
        assert d["payload_bytes"] == 5
        assert d["payload"] == "hello"

    def test_to_json_is_valid(self):
        import json

        record = self._make_record()
        parsed = json.loads(record.to_json())
        assert parsed["remote_ip"] == "192.168.1.50"

    def test_str_representation(self):
        record = self._make_record(payload=b"abc")
        s = str(record)
        assert "192.168.1.50" in s
        assert "54321" in s
        assert "8080" in s
        assert "3 bytes" in s

    def test_payload_text_invalid_utf8(self):
        record = self._make_record(payload=b"\xff\xfe")
        # Should not raise, invalid bytes replaced
        text = record.payload_text()
        assert isinstance(text, str)

    def test_explicit_timestamp(self):
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = CaptureRecord(
            remote_ip="1.2.3.4",
            remote_port=1234,
            local_port=22,
            timestamp=ts,
        )
        assert record.timestamp == ts
        assert "2025-01-01" in record.to_dict()["timestamp"]

    def test_default_timestamp_is_utc(self):
        record = self._make_record()
        assert record.timestamp.tzinfo is not None


class TestBuildLogger:
    def test_returns_logger(self):
        logger = build_logger("test_build_logger_unique")
        assert isinstance(logger, logging.Logger)

    def test_idempotent(self):
        name = "test_idempotent_logger"
        logger1 = build_logger(name)
        handler_count = len(logger1.handlers)
        logger2 = build_logger(name)
        assert len(logger2.handlers) == handler_count

    def test_log_capture_emits(self, caplog):
        import logging

        record = CaptureRecord(
            remote_ip="10.0.0.1",
            remote_port=12345,
            local_port=2222,
            payload=b"test payload",
        )
        logger = logging.getLogger("test_log_capture_emits")
        logger.setLevel(logging.DEBUG)
        with caplog.at_level(logging.DEBUG, logger="test_log_capture_emits"):
            log_capture(logger, record)
        # At least one log record should mention the IP
        assert any("10.0.0.1" in m for m in caplog.messages)
