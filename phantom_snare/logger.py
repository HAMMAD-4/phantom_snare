"""Structured logging for phantom_snare capture events."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class CaptureRecord:
    """Represents a single captured connection attempt."""

    def __init__(
        self,
        *,
        remote_ip: str,
        remote_port: int,
        local_port: int,
        payload: bytes = b"",
        timestamp: Optional[datetime] = None,
    ) -> None:
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.local_port = local_port
        self.payload = payload
        self.timestamp = timestamp or datetime.now(tz=timezone.utc)

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------

    def payload_text(self) -> str:
        """Return the payload decoded as UTF-8, replacing undecodable bytes."""
        return self.payload.decode("utf-8", errors="replace")

    def to_dict(self) -> dict:
        """Serialise the record to a plain dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "remote_ip": self.remote_ip,
            "remote_port": self.remote_port,
            "local_port": self.local_port,
            "payload_bytes": len(self.payload),
            "payload": self.payload_text(),
        }

    def to_json(self) -> str:
        """Return a compact JSON string representation."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.isoformat()}] "
            f"{self.remote_ip}:{self.remote_port} -> port {self.local_port} "
            f"({len(self.payload)} bytes)"
        )


def build_logger(name: str = "phantom_snare", log_file: Optional[str] = None) -> logging.Logger:
    """Construct and return a configured :class:`logging.Logger`.

    The logger writes JSON-formatted capture lines so that log files can be
    easily parsed by external tools (e.g., Splunk, ELK).

    Args:
        name:     Logger name.
        log_file: If provided, log entries are *also* written to this file.

    Returns:
        A ready-to-use :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        # Avoid adding duplicate handlers if called multiple times
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")

    # Always log to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_capture(logger: logging.Logger, record: CaptureRecord) -> None:
    """Write a structured JSON capture entry to *logger*.

    Args:
        logger: Destination logger.
        record: The capture event to log.
    """
    logger.info(record.to_json())
