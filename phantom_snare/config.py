import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    ports: List[int] = field(default_factory=lambda: [2222, 8080, 2121])
    bind_address: str = "0.0.0.0"
    max_payload_bytes: int = 4096
    log_file: Optional[str] = "phantom_snare.log"
    max_connections: int = 50
    banner: str = "Welcome\r\n"
    db_enabled: bool = False
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "phantom_snare"
    alert_email_to: Optional[str] = None
    alert_email_from: Optional[str] = None
    alert_smtp_host: Optional[str] = None
    alert_smtp_port: int = 587
    alert_smtp_user: Optional[str] = None
    alert_smtp_password: Optional[str] = None
    evidence_db: str = "phantom_snare_evidence.db"
    dashboard_enabled: bool = True
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 5000
    max_connections_per_minute: int = 20

    @classmethod
    def from_file(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in config file '{path}': {exc}") from exc
        valid_fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_file(self, path: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.__dict__, fh, indent=2)

    @property
    def email_alerts_enabled(self) -> bool:
        return all(
            [
                self.alert_email_to,
                self.alert_email_from,
                self.alert_smtp_host,
                self.alert_smtp_user,
                self.alert_smtp_password,
            ]
        )
