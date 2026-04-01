"""Tests for phantom_snare.deceptor (Deceptor module)."""

import pytest

from phantom_snare.deceptor import Deceptor, HoneyToken, _make_corrupted_payload
from phantom_snare.sqlite_db import EvidenceStore


@pytest.fixture
def store(tmp_path):
    s = EvidenceStore(str(tmp_path / "dec_test.db"))
    s.connect()
    yield s
    s.close()


class TestHoneyToken:
    def test_token_has_unique_id(self):
        t1 = HoneyToken("/admin")
        t2 = HoneyToken("/admin")
        assert t1.token_id != t2.token_id

    def test_to_dict_keys(self):
        t = HoneyToken("/secret", "test token")
        d = t.to_dict()
        assert set(d.keys()) == {"token_id", "path", "description"}
        assert d["path"] == "/secret"


class TestDeceptorInit:
    def test_registers_honey_tokens(self, store):
        d = Deceptor(evidence_store=store)
        assert len(d.get_honey_tokens()) > 0

    def test_default_token_paths_include_common_targets(self, store):
        d = Deceptor(evidence_store=store)
        paths = d.get_honey_token_paths()
        assert "/.env" in paths
        assert "/admin" in paths
        assert "/wp-admin" in paths


class TestHoneyTokenMatching:
    def test_exact_path_match(self, store):
        d = Deceptor(evidence_store=store)
        result = d.check_honey_token("/.env", "1.2.3.4", "test")
        assert result is not None

    def test_prefix_path_match(self, store):
        d = Deceptor(evidence_store=store)
        # /admin/something should match the /admin token
        result = d.check_honey_token("/admin/config", "1.2.3.4")
        assert result is not None

    def test_non_honey_path_returns_none(self, store):
        d = Deceptor(evidence_store=store)
        result = d.check_honey_token("/this/is/a/normal/path", "1.2.3.4")
        assert result is None

    def test_hit_is_persisted(self, store):
        d = Deceptor(evidence_store=store)
        d.check_honey_token("/.env", "9.9.9.9", "test hit")
        hits = store.get_honey_token_hits()
        assert any(h["remote_ip"] == "9.9.9.9" for h in hits)

    def test_query_string_stripped(self, store):
        d = Deceptor(evidence_store=store)
        result = d.check_honey_token("/.env?debug=1", "1.2.3.4")
        assert result is not None

    def test_case_insensitive_match(self, store):
        d = Deceptor(evidence_store=store)
        result = d.check_honey_token("/.ENV", "1.2.3.4")
        assert result is not None


class TestDeceptivePayloads:
    def test_http_response_is_bytes(self, store):
        d = Deceptor(evidence_store=store)
        resp = d.get_deceptive_http_response("1.2.3.4")
        assert isinstance(resp, bytes)
        assert b"HTTP/1.1 200 OK" in resp

    def test_http_response_contains_fake_html(self, store):
        d = Deceptor(evidence_store=store)
        resp = d.get_deceptive_http_response()
        assert b"<html" in resp
        assert b"password" in resp.lower()

    def test_corrupted_payload_is_bytes(self, store):
        d = Deceptor(evidence_store=store)
        payload = d.get_corrupted_payload("1.2.3.4", size_bytes=1024)
        assert isinstance(payload, bytes)
        assert len(payload) == 1024

    def test_corrupted_payload_has_zip_magic(self, store):
        d = Deceptor(evidence_store=store)
        payload = d.get_corrupted_payload()
        assert payload[:2] == b"PK"

    def test_make_corrupted_payload_size(self):
        p = _make_corrupted_payload(4096)
        assert len(p) == 4096

    def test_financial_data_is_csv(self, store):
        d = Deceptor(evidence_store=store)
        data = d.get_fake_financial_data()
        assert b"Account" in data
        assert b"Balance" in data
