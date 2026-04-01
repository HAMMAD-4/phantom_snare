"""Tests for phantom_snare.observer (Observer module)."""

from datetime import datetime, timezone

import pytest

from phantom_snare.logger import CaptureRecord
from phantom_snare.observer import Observer, _RISK_HIGH_COUNT, _RISK_MEDIUM_COUNT
from phantom_snare.sqlite_db import EvidenceStore


def _make_record(ip="10.0.0.1", port=2222, payload=b"GET / HTTP/1.0\r\n"):
    return CaptureRecord(
        remote_ip=ip,
        remote_port=54321,
        local_port=port,
        payload=payload,
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def store(tmp_path):
    s = EvidenceStore(str(tmp_path / "obs_test.db"))
    s.connect()
    yield s
    s.close()


class TestObserverRiskScoring:
    def test_zero_connections_score_zero(self):
        obs = Observer()
        assert obs.compute_risk_score("unknown") == 0

    def test_low_risk_score(self):
        obs = Observer()
        for _ in range(2):
            obs.on_capture(_make_record())
        score = obs.compute_risk_score("10.0.0.1")
        assert score < 30

    def test_medium_risk_score(self):
        obs = Observer()
        for _ in range(_RISK_MEDIUM_COUNT):
            obs.on_capture(_make_record())
        score = obs.compute_risk_score("10.0.0.1")
        assert 30 <= score < 60

    def test_high_risk_score(self):
        obs = Observer()
        for _ in range(_RISK_HIGH_COUNT):
            obs.on_capture(_make_record())
        score = obs.compute_risk_score("10.0.0.1")
        assert score >= 60

    def test_risk_label(self):
        assert Observer.risk_label(0) == "LOW"
        assert Observer.risk_label(29) == "LOW"
        assert Observer.risk_label(30) == "MEDIUM"
        assert Observer.risk_label(59) == "MEDIUM"
        assert Observer.risk_label(60) == "HIGH"
        assert Observer.risk_label(100) == "HIGH"


class TestObserverAutoBlock:
    def test_auto_blocks_high_risk_ip(self, store):
        from phantom_snare.shield import Shield

        shield = Shield(evidence_store=store, max_connections_per_minute=1000)
        obs = Observer(evidence_store=store, shield=shield)

        ip = "1.2.3.4"
        for _ in range(_RISK_HIGH_COUNT):
            obs.on_capture(_make_record(ip=ip))

        assert shield.is_blocked(ip)


class TestObserverPatternDetection:
    def test_http_probe_logged(self, store):
        obs = Observer(evidence_store=store)
        obs.on_capture(_make_record(payload=b"GET /admin HTTP/1.1\r\nHost: x\r\n\r\n"))
        events = store.get_recent_events()
        types = [e["event_type"] for e in events]
        assert "HTTP_PROBE" in types

    def test_credential_probe_logged(self, store):
        obs = Observer(evidence_store=store)
        obs.on_capture(_make_record(payload=b"password=secret&username=admin"))
        events = store.get_recent_events()
        types = [e["event_type"] for e in events]
        assert "CREDENTIAL_PROBE" in types

    def test_traversal_logged(self, store):
        obs = Observer(evidence_store=store)
        obs.on_capture(_make_record(payload=b"GET /../../../etc/passwd HTTP/1.0\r\n"))
        events = store.get_recent_events()
        types = [e["event_type"] for e in events]
        assert "TRAVERSAL_ATTEMPT" in types

    def test_port_scan_probe_logged(self, store):
        obs = Observer(evidence_store=store)
        obs.on_capture(_make_record(payload=b""))
        events = store.get_recent_events()
        types = [e["event_type"] for e in events]
        assert "PORT_SCAN_PROBE" in types


class TestObserverRiskSummary:
    def test_risk_summary_contains_ip(self):
        obs = Observer()
        obs.on_capture(_make_record(ip="5.5.5.5"))
        summary = obs.get_ip_risk_summary()
        ips = [entry["ip"] for entry in summary]
        assert "5.5.5.5" in ips

    def test_risk_summary_sorted_by_connections(self):
        obs = Observer()
        for _ in range(5):
            obs.on_capture(_make_record(ip="high-risk"))
        obs.on_capture(_make_record(ip="low-risk"))
        summary = obs.get_ip_risk_summary()
        assert summary[0]["ip"] == "high-risk"


class TestObserverUrlClassification:
    def test_honey_path_classified_harmful(self, store):
        from phantom_snare.deceptor import Deceptor
        deceptor = Deceptor(evidence_store=store)
        obs = Observer(evidence_store=store, deceptor=deceptor)
        payload = b"GET /.env HTTP/1.1\r\nHost: target.com\r\n\r\n"
        obs.on_capture(_make_record(payload=payload))
        visits = store.get_recent_site_visits()
        harmful = [v for v in visits if v["is_harmful"] == 1]
        assert len(harmful) >= 1
        assert "/.env" in harmful[0]["path"] or harmful[0]["harm_reason"]

    def test_safe_path_not_harmful(self, store):
        obs = Observer(evidence_store=store)
        payload = b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"
        obs.on_capture(_make_record(payload=payload))
        visits = store.get_recent_site_visits()
        assert len(visits) >= 1
        assert visits[0]["is_harmful"] == 0

    def test_harmful_url_event_logged(self, store):
        from phantom_snare.deceptor import Deceptor
        deceptor = Deceptor(evidence_store=store)
        obs = Observer(evidence_store=store, deceptor=deceptor)
        payload = b"GET /wp-admin HTTP/1.1\r\nHost: victim.com\r\n\r\n"
        obs.on_capture(_make_record(payload=payload))
        events = store.get_recent_events()
        types = [e["event_type"] for e in events]
        assert "HARMFUL_URL_DETECTED" in types

    def test_host_extracted_from_payload(self, store):
        obs = Observer(evidence_store=store)
        payload = b"GET /page HTTP/1.1\r\nHost: mysite.example.com\r\n\r\n"
        obs.on_capture(_make_record(payload=payload))
        visits = store.get_recent_site_visits()
        assert visits[0]["host"] == "mysite.example.com"

    def test_traversal_path_classified_harmful(self, store):
        obs = Observer(evidence_store=store)
        payload = b"GET /../etc/passwd HTTP/1.1\r\nHost: h\r\n\r\n"
        obs.on_capture(_make_record(payload=payload))
        visits = store.get_recent_site_visits()
        harmful = [v for v in visits if v["is_harmful"] == 1]
        assert len(harmful) >= 1
