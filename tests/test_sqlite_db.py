"""Tests for phantom_snare.sqlite_db (EvidenceStore)."""

import os
import tempfile
from datetime import datetime, timezone

import pytest

from phantom_snare.logger import CaptureRecord
from phantom_snare.sqlite_db import EvidenceStore


def _make_record(ip="10.0.0.1", port=80, payload=b"GET / HTTP/1.0\r\n"):
    return CaptureRecord(
        remote_ip=ip,
        remote_port=54321,
        local_port=port,
        payload=payload,
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = EvidenceStore(db_path=db_path)
    s.connect()
    yield s
    s.close()


class TestEvidenceStoreLifecycle:
    def test_connect_and_close(self, tmp_path):
        s = EvidenceStore(str(tmp_path / "t.db"))
        s.connect()
        s.close()

    def test_context_manager(self, tmp_path):
        with EvidenceStore(str(tmp_path / "t.db")) as s:
            assert s._conn is not None
        assert s._conn is None


class TestCaptures:
    def test_save_and_retrieve(self, store):
        store.save_capture(_make_record())
        rows = store.get_recent_captures()
        assert len(rows) == 1
        assert rows[0]["remote_ip"] == "10.0.0.1"

    def test_multiple_captures(self, store):
        for i in range(5):
            store.save_capture(_make_record(ip=f"10.0.0.{i}"))
        rows = store.get_recent_captures()
        assert len(rows) == 5

    def test_limit(self, store):
        for i in range(20):
            store.save_capture(_make_record())
        rows = store.get_recent_captures(limit=5)
        assert len(rows) == 5

    def test_ip_stats(self, store):
        store.save_capture(_make_record(ip="1.2.3.4"))
        store.save_capture(_make_record(ip="1.2.3.4"))
        store.save_capture(_make_record(ip="5.6.7.8"))
        stats = store.get_ip_stats()
        ips = {s["remote_ip"]: s["total_connections"] for s in stats}
        assert ips["1.2.3.4"] == 2
        assert ips["5.6.7.8"] == 1


class TestEvents:
    def test_save_event(self, store):
        store.save_event("TEST_EVENT", "1.2.3.4", "detail text")
        events = store.get_recent_events()
        assert any(e["event_type"] == "TEST_EVENT" for e in events)

    def test_recent_events_limit(self, store):
        for i in range(20):
            store.save_event("EVT", f"10.0.0.{i}", "")
        events = store.get_recent_events(limit=5)
        assert len(events) == 5


class TestBlockedIPs:
    def test_block_and_check(self, store):
        assert not store.is_blocked("1.2.3.4")
        store.block_ip("1.2.3.4", "test reason")
        assert store.is_blocked("1.2.3.4")

    def test_unblock(self, store):
        store.block_ip("1.2.3.4")
        store.unblock_ip("1.2.3.4")
        assert not store.is_blocked("1.2.3.4")

    def test_get_blocked_ips(self, store):
        store.block_ip("1.2.3.4", "r1")
        store.block_ip("5.6.7.8", "r2")
        blocked = store.get_blocked_ips()
        ips = [b["ip"] for b in blocked]
        assert "1.2.3.4" in ips
        assert "5.6.7.8" in ips

    def test_block_replace(self, store):
        store.block_ip("1.2.3.4", "old reason")
        store.block_ip("1.2.3.4", "new reason")
        blocked = store.get_blocked_ips()
        entry = next(b for b in blocked if b["ip"] == "1.2.3.4")
        assert entry["reason"] == "new reason"


class TestHoneyTokens:
    def test_register_and_hit(self, store):
        store.register_honey_token("tok1", "/secret", "Test token")
        store.record_honey_token_hit("tok1", "1.2.3.4", "test access")
        hits = store.get_honey_token_hits()
        assert len(hits) == 1
        assert hits[0]["remote_ip"] == "1.2.3.4"

    def test_hit_count(self, store):
        store.register_honey_token("tok2", "/admin", "admin token")
        for _ in range(3):
            store.record_honey_token_hit("tok2", "5.5.5.5", "")
        assert store.get_honey_token_hit_count() == 3


class TestSiteVisits:
    def test_save_safe_visit(self, store):
        store.save_site_visit("1.2.3.4", "example.com", "/index.html", "GET", False, "")
        visits = store.get_recent_site_visits()
        assert len(visits) == 1
        v = visits[0]
        assert v["remote_ip"] == "1.2.3.4"
        assert v["host"] == "example.com"
        assert v["path"] == "/index.html"
        assert v["method"] == "GET"
        assert v["is_harmful"] == 0

    def test_save_harmful_visit(self, store):
        store.save_site_visit("5.6.7.8", "target.com", "/.env", "GET", True, "Honey token path")
        visits = store.get_recent_site_visits()
        assert any(v["is_harmful"] == 1 for v in visits)
        harmful = [v for v in visits if v["is_harmful"] == 1]
        assert harmful[0]["harm_reason"] == "Honey token path"

    def test_multiple_visits_limit(self, store):
        for i in range(10):
            store.save_site_visit(f"10.0.0.{i}", "host.com", f"/path{i}", "GET", False)
        visits = store.get_recent_site_visits(limit=3)
        assert len(visits) == 3

    def test_empty_site_visits(self, store):
        visits = store.get_recent_site_visits()
        assert visits == []
