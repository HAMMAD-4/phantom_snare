"""Module 3: Deceptor – Active Deception & Data Poisoning.

The Deceptor is phantom_snare's active-defence layer.  It operates in three
ways:

1. **Honey-Tokening** – Fake high-value paths (``/.env``, ``/wp-admin``,
   ``/passwords.txt``, etc.) are pre-registered.  When the Observer detects
   that an incoming HTTP request targets one of these paths the Deceptor
   records the hit as high-confidence evidence of malicious intent.

2. **Deceptive HTTP responses** – Blocked IPs that send HTTP traffic receive
   a convincing fake login page that contains plausible-but-useless
   credentials in HTML comments (data poisoning).

3. **Corrupted binary payloads** – Non-HTTP blocked connections receive
   a ZIP-magic-prefixed binary blob that appears to be a valid archive but
   contains only garbage, designed to waste the attacker's parsing resources.
"""

import logging
import os
import random
import string
import uuid
from typing import List, Optional

_module_logger = logging.getLogger("phantom_snare.deceptor")

# ---------------------------------------------------------------------------
# Honey-token path registry
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Deceptive HTTP response template
# ---------------------------------------------------------------------------

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
    """Return a ZIP-magic-prefixed binary blob that looks valid but is garbage.

    Designed to waste attacker parser resources (zip-bomb style).
    """
    # ZIP local file header signature
    header = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
    marker = b"PHANTOM_SNARE_DECEPTION_PAYLOAD_v1\r\n"
    # Pad with pseudo-random bytes to the requested size
    payload = header + marker
    remaining = max(0, size_bytes - len(payload))
    payload += os.urandom(remaining)
    return payload[:size_bytes]


# ---------------------------------------------------------------------------
# HoneyToken data class
# ---------------------------------------------------------------------------


class HoneyToken:
    """A single registered honey-token path."""

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


# ---------------------------------------------------------------------------
# Deceptor class
# ---------------------------------------------------------------------------


class Deceptor:
    """Active-deception module.

    Args:
        evidence_store: Shared SQLite evidence store.  Used to persist
            honey-token hits and forensic events.
    """

    def __init__(self, evidence_store=None) -> None:
        self._store = evidence_store
        self._tokens: List[HoneyToken] = []
        self._register_default_tokens()

    # ------------------------------------------------------------------
    # Honey-token management
    # ------------------------------------------------------------------

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
        """Return all registered honey tokens as a list of dicts."""
        return [t.to_dict() for t in self._tokens]

    def get_honey_token_paths(self) -> List[str]:
        """Return all honey-token paths."""
        return [t.path for t in self._tokens]

    def check_honey_token(
        self, path: str, remote_ip: str, details: str = ""
    ) -> Optional[str]:
        """Check whether *path* matches a honey token and record a hit.

        Args:
            path:      URL path from the HTTP request.
            remote_ip: Connecting IP address.
            details:   Extra context (e.g. first line of request).

        Returns:
            The ``token_id`` if a match is found, otherwise ``None``.
        """
        path_lower = path.lower().split("?", 1)[0]  # strip query string
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

    # ------------------------------------------------------------------
    # Deceptive payload generators
    # ------------------------------------------------------------------

    def get_deceptive_http_response(self, remote_ip: str = "unknown") -> bytes:
        """Return a convincing but fake HTTP 200 response.

        The HTML body contains plausible-but-garbage database credentials
        in an HTML comment to poison the attacker's data collection.
        """
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
        """Return a corrupted binary payload for non-HTTP connections.

        The payload has a valid ZIP header but garbage content, intended to
        consume parser resources on the attacker's infrastructure.
        """
        _module_logger.info(
            "[Deceptor] Sending %d-byte corrupted payload to %s",
            size_bytes,
            remote_ip,
        )
        return _make_corrupted_payload(size_bytes)

    def get_fake_financial_data(self) -> bytes:
        """Return a fake financial CSV that looks like a real export.

        Placed in honey-token paths to satisfy directory crawlers.
        """
        lines = [b"Account,Holder,Balance,IBAN\r\n"]
        for _ in range(20):
            account = "".join(random.choices(string.digits, k=10))
            holder = "".join(random.choices(string.ascii_uppercase, k=6))
            balance = f"{random.uniform(100, 99999):.2f}"
            iban = "GB" + "".join(random.choices(string.digits, k=20))
            lines.append(f"{account},{holder},{balance},{iban}\r\n".encode())
        return b"".join(lines)
