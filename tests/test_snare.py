"""Tests for phantom_snare.snare (integration-level, uses real sockets)."""

import socket
import threading
import time

import pytest

from phantom_snare.config import Config
from phantom_snare.snare import Snare


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
