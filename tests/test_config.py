"""Tests for phantom_snare.config."""

import json
import os
import tempfile

import pytest

from phantom_snare.config import Config


class TestConfigDefaults:
    def test_default_ports(self):
        cfg = Config()
        assert cfg.ports == [2222, 8080, 2121]

    def test_default_bind_address(self):
        cfg = Config()
        assert cfg.bind_address == "0.0.0.0"

    def test_default_max_payload_bytes(self):
        cfg = Config()
        assert cfg.max_payload_bytes == 4096

    def test_default_banner(self):
        cfg = Config()
        assert cfg.banner == "Welcome\r\n"

    def test_email_alerts_disabled_by_default(self):
        cfg = Config()
        assert not cfg.email_alerts_enabled


class TestConfigFromFile:
    def _write_json(self, data: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh)
        return path

    def test_load_ports(self):
        path = self._write_json({"ports": [9999, 1234]})
        cfg = Config.from_file(path)
        assert cfg.ports == [9999, 1234]
        os.unlink(path)

    def test_unknown_keys_ignored(self):
        path = self._write_json({"unknown_key": "value", "ports": [22]})
        cfg = Config.from_file(path)
        assert cfg.ports == [22]
        os.unlink(path)

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            Config.from_file("/nonexistent/path/config.json")

    def test_invalid_json_raises(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("not valid json {{{")
        with pytest.raises(ValueError, match="Invalid JSON"):
            Config.from_file(path)
        os.unlink(path)


class TestConfigToFile:
    def test_roundtrip(self):
        cfg = Config(ports=[1111, 2222], bind_address="127.0.0.1")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.json")
            cfg.to_file(path)
            loaded = Config.from_file(path)
        assert loaded.ports == [1111, 2222]
        assert loaded.bind_address == "127.0.0.1"


class TestEmailAlertsEnabled:
    def test_all_fields_set(self):
        cfg = Config(
            alert_email_to="to@example.com",
            alert_email_from="from@example.com",
            alert_smtp_host="smtp.example.com",
            alert_smtp_user="user",
            alert_smtp_password="secret",
        )
        assert cfg.email_alerts_enabled

    def test_partial_fields_not_enabled(self):
        cfg = Config(alert_email_to="to@example.com")
        assert not cfg.email_alerts_enabled
