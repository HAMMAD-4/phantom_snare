"""Tests for phantom_snare.vault (Vault dashboard API)."""

import json

import pytest

from phantom_snare.deceptor import Deceptor
from phantom_snare.observer import Observer
from phantom_snare.shield import Shield
from phantom_snare.sqlite_db import EvidenceStore
from phantom_snare.vault import Vault


@pytest.fixture
def store(tmp_path):
    s = EvidenceStore(str(tmp_path / "vault_test.db"))
    s.connect()
    yield s
    s.close()


@pytest.fixture
def vault(store):
    shield = Shield(evidence_store=store)
    deceptor = Deceptor(evidence_store=store)
    observer = Observer(evidence_store=store, shield=shield, deceptor=deceptor)
    v = Vault(
        evidence_store=store,
        shield=shield,
        observer=observer,
        deceptor=deceptor,
    )
    return v


@pytest.fixture
def client(vault):
    vault._app.config["TESTING"] = True
    with vault._app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /api/block
# ---------------------------------------------------------------------------


class TestApiBlock:
    def test_block_valid_ipv4(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "1.2.3.4", "reason": "test"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["ok"] is True
        assert store.is_blocked("1.2.3.4")

    def test_block_valid_ipv6(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "::1"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert store.is_blocked("::1")

    def test_block_invalid_ip_returns_400(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "not-an-ip"}),
            content_type="application/json",
        )
        assert r.status_code == 400
        body = r.get_json()
        assert "Invalid IP address" in body["error"]
        assert not store.is_blocked("not-an-ip")

    def test_block_ip_with_port_returns_400(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "1.2.3.4:8080"}),
            content_type="application/json",
        )
        assert r.status_code == 400
        assert not store.is_blocked("1.2.3.4:8080")

    def test_block_empty_ip_returns_400(self, client):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400
        body = r.get_json()
        assert "ip is required" in body["error"]

    def test_block_missing_ip_returns_400(self, client):
        r = client.post(
            "/api/block",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_block_null_reason_uses_default(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "5.6.7.8", "reason": None}),
            content_type="application/json",
        )
        assert r.status_code == 200
        blocked = store.get_blocked_ips()
        entry = next(b for b in blocked if b["ip"] == "5.6.7.8")
        # reason must NOT be the string "None"
        assert entry["reason"] != "None"
        assert entry["reason"]  # non-empty

    def test_block_empty_reason_uses_default(self, client, store):
        r = client.post(
            "/api/block",
            data=json.dumps({"ip": "9.8.7.6", "reason": ""}),
            content_type="application/json",
        )
        assert r.status_code == 200
        blocked = store.get_blocked_ips()
        entry = next(b for b in blocked if b["ip"] == "9.8.7.6")
        assert entry["reason"]  # non-empty (uses default)


# ---------------------------------------------------------------------------
# /api/unblock
# ---------------------------------------------------------------------------


class TestApiUnblock:
    def test_unblock_valid_ip(self, client, store):
        store.block_ip("1.2.3.4", "test")
        r = client.post(
            "/api/unblock",
            data=json.dumps({"ip": "1.2.3.4"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True
        assert not store.is_blocked("1.2.3.4")

    def test_unblock_invalid_ip_returns_400(self, client):
        r = client.post(
            "/api/unblock",
            data=json.dumps({"ip": "bad-ip"}),
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "Invalid IP address" in r.get_json()["error"]

    def test_unblock_empty_ip_returns_400(self, client):
        r = client.post(
            "/api/unblock",
            data=json.dumps({"ip": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Other API endpoints
# ---------------------------------------------------------------------------


class TestApiStatus:
    def test_status_ok(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        body = r.get_json()
        assert body["status"] == "running"


class TestApiCaptures:
    def test_captures_returns_list(self, client):
        r = client.get("/api/captures")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)


class TestApiEvents:
    def test_events_returns_list(self, client):
        r = client.get("/api/events")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)


class TestApiBlocked:
    def test_blocked_returns_list(self, client):
        r = client.get("/api/blocked")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_blocked_shows_entry(self, client, store):
        store.block_ip("3.3.3.3", "manual")
        r = client.get("/api/blocked")
        ips = [e["ip"] for e in r.get_json()]
        assert "3.3.3.3" in ips
