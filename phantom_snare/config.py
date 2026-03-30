"""Configuration management for phantom_snare."""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Holds all runtime configuration for the honeypot."""

    # Ports to listen on (each becomes a separate honeypot listener)
    ports: List[int] = field(default_factory=lambda: [2222, 8080, 2121])

    # Network interface to bind to ("0.0.0.0" means all interfaces)
    bind_address: str = "0.0.0.0"

    # Maximum number of bytes to read from an incoming connection
    max_payload_bytes: int = 4096

    # Path to the log file (None = log to stdout only)
    log_file: Optional[str] = "phantom_snare.log"

    # Maximum number of concurrent connections per listener
    max_connections: int = 50

    # Banner sent to connecting clients (makes the honeypot look like a real service)
    banner: str = "Welcome\r\n"

    # MySQL database settings
    db_enabled: bool = False
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "phantom_snare"

    # Email alert settings (all must be set to enable email alerts)
    alert_email_to: Optional[str] = None
    alert_email_from: Optional[str] = None
    alert_smtp_host: Optional[str] = None
    alert_smtp_port: int = 587
    alert_smtp_user: Optional[str] = None
    alert_smtp_password: Optional[str] = None

    # ----------------------------------------------------------------
    # HIDPS module settings
    # ----------------------------------------------------------------

    # SQLite evidence database path (used by all four HIDPS modules)
    evidence_db: str = "phantom_snare_evidence.db"

    # Vault dashboard settings
    dashboard_enabled: bool = True
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 5000

    # Shield rate-limit threshold (connections per 60-second rolling window)
    max_connections_per_minute: int = 20

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from a JSON file.

        Missing keys fall back to dataclass defaults.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            A populated :class:`Config` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError: If the file contains invalid JSON.
        """
        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in config file '{path}': {exc}") from exc

        valid_fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_file(self, path: str) -> None:
        """Persist the current configuration to *path* as JSON.

        Args:
            path: Destination file path.
        """
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.__dict__, fh, indent=2)

    @property
    def email_alerts_enabled(self) -> bool:
        """Return *True* when all required email fields are configured."""
        return all(
            [
                self.alert_email_to,
                self.alert_email_from,
                self.alert_smtp_host,
                self.alert_smtp_user,
                self.alert_smtp_password,
            ]
        )
