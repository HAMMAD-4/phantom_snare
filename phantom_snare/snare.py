"""Core honeypot listener for phantom_snare.

Each :class:`Snare` instance manages a pool of TCP listeners (one per
configured port).  Incoming connections are accepted, a banner is sent,
any payload is read, the event is logged, and an optional email alert
is dispatched – all without blocking other listeners.
"""

import errno
import logging
import socket
import threading
from typing import List, Optional

from .alerts import send_alert
from .config import Config
from .database import DatabaseManager
from .logger import CaptureRecord, build_logger, log_capture

_module_logger = logging.getLogger("phantom_snare.snare")


class Snare:
    """Orchestrates honeypot listeners across one or more TCP ports.

    Usage::

        cfg = Config(ports=[2222, 8080])
        snare = Snare(cfg)
        snare.start()      # non-blocking – listeners run in daemon threads
        # … do other work, or simply block …
        snare.stop()

    Args:
        config: Runtime configuration.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self._logger = build_logger(log_file=self.config.log_file)
        self._db: Optional[DatabaseManager] = None
        self._server_sockets: List[socket.socket] = []
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open listener sockets and start accept-loop threads.

        Returns immediately; all I/O happens in daemon threads.
        """
        self._stop_event.clear()

        # Connect to MySQL if enabled
        if self.config.db_enabled:
            self._db = DatabaseManager(self.config)
            try:
                self._db.connect()
            except Exception as exc:  # pylint: disable=broad-except
                _module_logger.error("MySQL connection failed: %s", exc)
                self._db = None

        for port in self.config.ports:
            self._start_listener(port)

        bound_ports = [sock.getsockname()[1] for sock in self._server_sockets]
        if bound_ports:
            _module_logger.info(
                "[phantom_snare] Listening on port(s): %s",
                ", ".join(str(p) for p in bound_ports),
            )
        else:
            _module_logger.error("[phantom_snare] No ports could be bound. Exiting.")

    def stop(self) -> None:
        """Signal all listeners to stop, close sockets, and disconnect from MySQL."""
        self._stop_event.set()
        for sock in self._server_sockets:
            try:
                sock.close()
            except OSError:
                pass
        for thread in self._threads:
            thread.join(timeout=2)
        self._server_sockets.clear()
        self._threads.clear()
        if self._db is not None:
            self._db.close()
            self._db = None
        _module_logger.info("phantom_snare stopped.")

    def run_forever(self) -> None:
        """Start listeners and block until :meth:`stop` is called or KeyboardInterrupt."""
        self.start()
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_listener(self, port: int) -> None:
        """Bind a TCP socket to *port* and spawn an accept-loop thread."""
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((self.config.bind_address, port))
            server_sock.listen(self.config.max_connections)
            server_sock.settimeout(1.0)  # allows periodic check of stop_event
            self._server_sockets.append(server_sock)
        except OSError as exc:
            # Build an actionable hint based on the specific error code.
            win_err = getattr(exc, "winerror", None)
            posix_err = getattr(exc, "errno", None)

            if win_err == 10013 or posix_err == errno.EACCES:
                hint = (
                    " – permission denied. "
                    "On Windows run as Administrator; "
                    "on Linux/macOS run with sudo or use a port > 1024."
                )
            elif win_err == 10048 or posix_err == errno.EADDRINUSE:
                hint = (
                    f" – port {port} is already in use by another process. "
                    "Choose a different port in your configuration."
                )
            else:
                hint = ""

            _module_logger.error("[phantom_snare] Cannot bind to port %d: %s%s", port, exc, hint)
            return

        thread = threading.Thread(
            target=self._accept_loop,
            args=(server_sock, port),
            daemon=True,
            name=f"snare-{port}",
        )
        thread.start()
        self._threads.append(thread)

    def _accept_loop(self, server_sock: socket.socket, port: int) -> None:
        """Accept connections on *server_sock* until the stop event is set."""
        while not self._stop_event.is_set():
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            handler = threading.Thread(
                target=self._handle_connection,
                args=(client_sock, addr, port),
                daemon=True,
            )
            handler.start()

    def _handle_connection(
        self, client_sock: socket.socket, addr: tuple, port: int
    ) -> None:
        """Process a single incoming connection.

        Sends the configured banner, reads any payload, logs the event, and
        sends an email alert if configured.
        """
        remote_ip, remote_port = addr[0], addr[1]
        try:
            # Send banner to make the service look real
            if self.config.banner:
                client_sock.sendall(self.config.banner.encode())

            # Read up to max_payload_bytes from the client
            client_sock.settimeout(5.0)
            try:
                payload = client_sock.recv(self.config.max_payload_bytes)
            except socket.timeout:
                payload = b""

        except OSError as exc:
            _module_logger.debug("Socket error for %s:%d: %s", remote_ip, remote_port, exc)
            payload = b""
        finally:
            try:
                client_sock.close()
            except OSError:
                pass

        record = CaptureRecord(
            remote_ip=remote_ip,
            remote_port=remote_port,
            local_port=port,
            payload=payload,
        )

        log_capture(self._logger, record)
        if self._db is not None:
            self._db.save_capture(record)
        send_alert(record, self.config)
