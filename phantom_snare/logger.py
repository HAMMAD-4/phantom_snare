import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class CaptureRecord:
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

    def payload_text(self) -> str:
        return self.payload.decode("utf-8", errors="replace")

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "remote_ip": self.remote_ip,
            "remote_port": self.remote_port,
            "local_port": self.local_port,
            "payload_bytes": len(self.payload),
            "payload": self.payload_text(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.isoformat()}] "
            f"{self.remote_ip}:{self.remote_port} -> port {self.local_port} "
            f"({len(self.payload)} bytes)"
        )


def build_logger(name: str = "phantom_snare", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_capture(logger: logging.Logger, record: CaptureRecord) -> None:
    logger.info(record.to_json())
