import logging
import os
import random
import string
import uuid
from typing import List, Optional

_module_logger = logging.getLogger("phantom_snare.deceptor")

_HONEY_PATHS: List[str] = [
    "/admin",
    "/admin/login",
    "/wp-admin",
    "/wp-admin/admin-ajax.php",
    "/.env",
    "/.git/config",
    "/config.php",
    "/config.json",
    "/.htpasswd",
    "/backup.zip",
    "/backup.sql",
    "/database.sql",
    "/db_backup.sql",
    "/passwords.txt",
    "/credentials.txt",
    "/api/keys",
    "/api/admin",
    "/api/v1/admin",
    "/financial/report.xlsx",
    "/bank_credentials.txt",
    "/secret.txt",
    "/private/keys",
    "/etc/passwd",
    "/etc/shadow",
    "/proc/version",
]

_DECEPTIVE_HTTP_TEMPLATE = (
    "HTTP/1.1 200 OK\r\n"
    "Server: Apache/2.4.54 (Ubuntu)\r\n"
    "Content-Type: text/html; charset=UTF-8\r\n"
    "X-Powered-By: PHP/8.1.12\r\n"
    "Set-Cookie: PHPSESSID={session_id}; path=/; HttpOnly\r\n"
    "Connection: close\r\n"
    "\r\n"
    "<!DOCTYPE html>\n"
    "<html lang='en'>\n"
    "<head><meta charset='UTF-8'><title>Admin Login</title></head>\n"
    "<body>\n"
    "<h2>Administration Panel</h2>\n"
    "<form method='post' action='/admin/auth'>\n"
    "  <label>Username: <input type='text' name='username' "
    "autocomplete='off'></label><br>\n"
    "  <label>Password: <input type='password' name='password'></label><br>\n"
    "  <input type='hidden' name='_token' value='{csrf_token}'>\n"
    "  <button type='submit'>Sign in</button>\n"
    "</form>\n"
    "<!-- DEBUG: db_pass={fake_db_password} db_host=localhost -->\n"
    "<!-- TODO: remove before production -->\n"
    "</body>\n"
    "</html>\r\n"
)


def _random_hex(length: int) -> str:
    return "".join(random.choices(string.hexdigits.lower(), k=length))


def _random_password(length: int = 18) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))


def _make_corrupted_payload(size_bytes: int = 32_768) -> bytes:
    header = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
    marker = b"PHANTOM_SNARE_DECEPTION_PAYLOAD_v1\r\n"
    payload = header + marker
    remaining = max(0, size_bytes - len(payload))
    payload += os.urandom(remaining)
    return payload[:size_bytes]


class HoneyToken:
    def __init__(self, path: str, description: str = "") -> None:
        self.token_id: str = str(uuid.uuid4())
        self.path: str = path
        self.description: str = description or f"Honey token at {path}"

    def to_dict(self) -> dict:
        return {
            "token_id": self.token_id,
            "path": self.path,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"HoneyToken(path={self.path!r})"


class Deceptor:
    def __init__(self, evidence_store=None) -> None:
        self._store = evidence_store
        self._tokens: List[HoneyToken] = []
        self._register_default_tokens()

    def _register_default_tokens(self) -> None:
        for path in _HONEY_PATHS:
            token = HoneyToken(path)
            self._tokens.append(token)
            if self._store is not None:
                self._store.register_honey_token(
                    token.token_id, token.path, token.description
                )
        _module_logger.info(
            "[Deceptor] %d honey tokens registered.", len(self._tokens)
        )

    def get_honey_tokens(self) -> List[dict]:
        return [t.to_dict() for t in self._tokens]

    def get_honey_token_paths(self) -> List[str]:
        return [t.path for t in self._tokens]

    def check_honey_token(
        self, path: str, remote_ip: str, details: str = ""
    ) -> Optional[str]:
        path_lower = path.lower().split("?", 1)[0]
        for token in self._tokens:
            token_lower = token.path.lower()
            if path_lower == token_lower or path_lower.startswith(token_lower):
                _module_logger.warning(
                    "[Deceptor] HONEY TOKEN HIT: %s accessed '%s'",
                    remote_ip,
                    path,
                )
                if self._store is not None:
                    self._store.record_honey_token_hit(
                        token.token_id, remote_ip, details
                    )
                    self._store.save_event(
                        "HONEY_TOKEN_HIT",
                        remote_ip,
                        f"Honey token '{path}' accessed",
                    )
                return token.token_id
        return None

    def get_deceptive_http_response(self, remote_ip: str = "unknown") -> bytes:
        session_id = _random_hex(26)
        csrf_token = _random_hex(32)
        fake_db_password = _random_password()

        response = _DECEPTIVE_HTTP_TEMPLATE.format(
            session_id=session_id,
            csrf_token=csrf_token,
            fake_db_password=fake_db_password,
        )
        _module_logger.info(
            "[Deceptor] Sending deceptive HTTP response to %s", remote_ip
        )
        return response.encode("utf-8")

    def get_corrupted_payload(
        self, remote_ip: str = "unknown", size_bytes: int = 32_768
    ) -> bytes:
        _module_logger.info(
            "[Deceptor] Sending %d-byte corrupted payload to %s",
            size_bytes,
            remote_ip,
        )
        return _make_corrupted_payload(size_bytes)

    def get_fake_financial_data(self) -> bytes:
        lines = [b"Account,Holder,Balance,IBAN\r\n"]
        for _ in range(20):
            account = "".join(random.choices(string.digits, k=10))
            holder = "".join(random.choices(string.ascii_uppercase, k=6))
            balance = f"{random.uniform(100, 99999):.2f}"
            iban = "GB" + "".join(random.choices(string.digits, k=20))
            lines.append(f"{account},{holder},{balance},{iban}\r\n".encode())
        return b"".join(lines)
