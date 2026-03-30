"""Tests for phantom_snare.shield (Shield module)."""

import time

import pytest

from phantom_snare.shield import Shield
from phantom_snare.sqlite_db import EvidenceStore


@pytest.fixture
def store(tmp_path):
    s = EvidenceStore(str(tmp_path / "shield_test.db"))
    s.connect()
    yield s
    s.close()


class TestShieldBasic:
    def test_allows_new_ip(self, store):
        shield = Shield(evidence_store=store, max_connections_per_minute=20)
        assert shield.check_and_record("1.2.3.4") is True

    def test_blocks_manually_added_ip(self, store):
        shield = Shield(evidence_store=store)
        shield.block_ip("1.2.3.4", "test")
        assert shield.check_and_record("1.2.3.4") is False

    def test_unblock(self, store):
        shield = Shield(evidence_store=store)
        shield.block_ip("1.2.3.4")
        shield.unblock_ip("1.2.3.4")
        assert shield.check_and_record("1.2.3.4") is True

    def test_is_blocked_false_by_default(self, store):
        shield = Shield(evidence_store=store)
        assert not shield.is_blocked("9.9.9.9")

    def test_is_blocked_true_after_block(self, store):
        shield = Shield(evidence_store=store)
        shield.block_ip("9.9.9.9")
        assert shield.is_blocked("9.9.9.9")


class TestShieldRateLimit:
    def test_auto_blocks_after_threshold(self, store):
        shield = Shield(evidence_store=store, max_connections_per_minute=5)
        ip = "2.3.4.5"
        # First 5 should be allowed
        for _ in range(5):
            shield.check_and_record(ip)
        # 6th should be blocked (rate exceeded)
        assert shield.check_and_record(ip) is False
        # Should now be in the persistent blocklist
        assert store.is_blocked(ip)

    def test_allows_below_threshold(self, store):
        shield = Shield(evidence_store=store, max_connections_per_minute=10)
        ip = "3.4.5.6"
        for _ in range(10):
            result = shield.check_and_record(ip)
        # At exactly max, the last call is still allowed (rate == max, not >)
        assert result is True

    def test_no_store_still_works(self):
        shield = Shield(evidence_store=None, max_connections_per_minute=5)
        ip = "4.5.6.7"
        for _ in range(5):
            shield.check_and_record(ip)
        # 6th connection should be rate-limited (blocked in-memory)
        assert shield.check_and_record(ip) is False
