"""Tests for phantom_snare.snare (integration-level, uses real sockets)."""

import socket
import threading
import time

import pytest

from phantom_snare.config import Config
from phantom_snare.deceptor import Deceptor
from phantom_snare.shield import Shield
from phantom_snare.snare import Snare
from phantom_snare.sqlite_db import EvidenceStore


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSnareLifecycle:
    def test_start_and_stop(self):
        port = _free_port()
        cfg = Config(ports=[port], bind_address="127.0.0.1", log_file=None)
        snare = Snare(cfg)
        snare.start()
        time.sleep(0.1)
        snare.stop()

    def test_stop_without_start_is_safe(self):
        cfg = Config(ports=[], bind_address="127.0.0.1", log_file=None)
        snare = Snare(cfg)
        snare.stop()  # Should not raise


class TestSnareConnections:
    def test_accepts_connection_and_sends_banner(self):
        port = _free_port()
        banner = "PHANTOM_TEST\r\n"
        cfg = Config(
            ports=[port],
            bind_address="127.0.0.1",
            banner=banner,
            log_file=None,
        )
        snare = Snare(cfg)
        snare.start()
        time.sleep(0.1)

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                data = conn.recv(256)
            assert data == banner.encode()
        finally:
            snare.stop()

    def test_captures_payload(self):
        """The snare should read the payload sent by the client without error."""
        port = _free_port()
        cfg = Config(
            ports=[port],
            bind_address="127.0.0.1",
            banner="",
            log_file=None,
        )
        snare = Snare(cfg)
        snare.start()
        time.sleep(0.1)

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.sendall(b"HELLO PHANTOM\r\n")
            # Give the handler thread time to process
            time.sleep(0.2)
        finally:
            snare.stop()

    def test_multiple_ports(self):
        port1, port2 = _free_port(), _free_port()
        cfg = Config(
            ports=[port1, port2],
            bind_address="127.0.0.1",
            banner="OK\r\n",
            log_file=None,
        )
        snare = Snare(cfg)
        snare.start()
        time.sleep(0.1)

        try:
            for port in (port1, port2):
                with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                    data = conn.recv(64)
                assert data == b"OK\r\n"
        finally:
            snare.stop()

    def test_no_banner(self):
        """Empty banner means no data is sent before reading payload."""
        port = _free_port()
        cfg = Config(
            ports=[port],
            bind_address="127.0.0.1",
            banner="",
            log_file=None,
        )
        snare = Snare(cfg)
        snare.start()
        time.sleep(0.1)

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.sendall(b"probe")
            time.sleep(0.2)
        finally:
            snare.stop()

    def test_run_forever_interrupted(self):
        """run_forever should stop cleanly on KeyboardInterrupt."""
        port = _free_port()
        cfg = Config(ports=[port], bind_address="127.0.0.1", log_file=None)
        snare = Snare(cfg)

        def _interrupt():
            time.sleep(0.15)
            snare.stop()

        t = threading.Thread(target=_interrupt, daemon=True)
        t.start()
        snare.run_forever()  # blocks until stop() is called
        t.join(timeout=2)


# ---------------------------------------------------------------------------
# Shield-integrated blocking tests
# ---------------------------------------------------------------------------

@pytest.fixture
def blocking_store(tmp_path):
    s = EvidenceStore(str(tmp_path / "snare_block_test.db"))
    s.connect()
    yield s
    s.close()


class TestSnareWithShield:
    """End-to-end tests verifying that the Shield's block list is enforced."""

    REAL_BANNER = "REAL_PHANTOM_BANNER\r\n"

    def _make_snare(self, port, store):
        shield = Shield(evidence_store=store, max_connections_per_minute=1000)
        deceptor = Deceptor(evidence_store=store)
        cfg = Config(
            ports=[port],
            bind_address="127.0.0.1",
            banner=self.REAL_BANNER,
            log_file=None,
        )
        return Snare(cfg, shield=shield, deceptor=deceptor), shield

    def test_non_blocked_ip_receives_real_banner(self, blocking_store):
        """A connection from an IP that is NOT blocked gets the real banner."""
        port = _free_port()
        snare, shield = self._make_snare(port, blocking_store)
        # Block a *different* IP so the shield is active
        shield.block_ip("10.0.0.99", "decoy")
        snare.start()
        time.sleep(0.1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.settimeout(2.0)
                data = conn.recv(256)
            assert data == self.REAL_BANNER.encode()
        finally:
            snare.stop()

    def test_blocked_ip_does_not_receive_real_banner(self, blocking_store):
        """A connection from a pre-blocked IP must NOT receive the real banner."""
        port = _free_port()
        snare, shield = self._make_snare(port, blocking_store)
        shield.block_ip("127.0.0.1", "test manual block")
        snare.start()
        time.sleep(0.1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.settimeout(2.0)
                data = b""
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    pass
            assert self.REAL_BANNER.encode() not in data, (
                f"Blocked IP received the real banner: {data!r}"
            )
        finally:
            snare.stop()

    def test_blocked_ip_receives_deceptive_payload(self, blocking_store):
        """A blocked IP must receive a non-empty deceptive response."""
        port = _free_port()
        snare, shield = self._make_snare(port, blocking_store)
        shield.block_ip("127.0.0.1", "test manual block")
        snare.start()
        time.sleep(0.1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.settimeout(2.0)
                data = b""
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    pass
            # The deceptor sends a corrupted binary payload for non-HTTP connections
            assert len(data) > 0, "Blocked IP received empty response (expected deceptive payload)"
        finally:
            snare.stop()

    def test_unblocked_ip_receives_real_banner_again(self, blocking_store):
        """After unblocking, the IP must receive the real banner again."""
        port = _free_port()
        snare, shield = self._make_snare(port, blocking_store)
        shield.block_ip("127.0.0.1", "temporary")
        shield.unblock_ip("127.0.0.1")
        snare.start()
        time.sleep(0.1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3) as conn:
                conn.settimeout(2.0)
                data = conn.recv(256)
            assert data == self.REAL_BANNER.encode()
        finally:
            snare.stop()

