# phantom_snare

> **Phantom-Snare** is a Host-based Intrusion Detection and Prevention System (HIDPS)
> that combines a multi-port TCP honeypot with four active-defence modules.
> Run it with a single command and open `http://127.0.0.1:5000` to see the live
> dashboard.

---

## Architecture – Four Modules

```
┌─────────────────────────────────────────────────────────────┐
│                    python main.py                           │
│                                                             │
│  Module 1 – Observer   │  Forensic evidence collection      │
│  Module 2 – Shield     │  IP blocking & rate limiting        │
│  Module 3 – Deceptor   │  Deceptive payloads & honey tokens  │
│  Module 4 – Vault      │  Web dashboard (http://…:5000)      │
│                                                             │
│  Shared: EvidenceStore │  SQLite – zero external DB needed  │
└─────────────────────────────────────────────────────────────┘
```

### Module 1 – Observer (Forensic Evidence Collection)
Wraps the core TCP honeypot and analyses every captured connection:
- Detects HTTP probes, credential keywords, directory-traversal patterns, port-scan
  probes (zero-byte connections)
- Computes per-IP risk scores (LOW / MEDIUM / HIGH) based on session connection count
- Automatically notifies the Shield when an IP crosses the high-risk threshold
- Checks incoming HTTP paths against the Deceptor's honey-token registry

### Module 2 – Shield (Neutralization & Blocking)
Enforces two protection mechanisms:
- **Static blocklist** – IPs added manually via the dashboard (or by the Observer)
  receive a deceptive response instead of the normal honeypot banner
- **Rate limiting** – Any IP that exceeds `max_connections_per_minute` (default: 20)
  is automatically added to the blocklist

### Module 3 – Deceptor (Active Deception & Data Poisoning)
Provides active-defence capabilities:
- **Honey tokens** – 25 high-value paths (`.env`, `/wp-admin`, `/passwords.txt`,
  etc.) are pre-registered; any access is recorded as high-confidence evidence of
  malicious intent
- **Deceptive HTTP responses** – Blocked HTTP clients receive a convincing fake login
  page with garbage credentials embedded in HTML comments (data poisoning)
- **Corrupted binary payloads** – Blocked non-HTTP clients receive a ZIP-magic-prefixed
  binary blob to waste attacker parser resources

### Module 4 – Vault (Dashboard & Command Centre)
Flask web dashboard served at `http://127.0.0.1:5000`:
- Real-time capture feed (auto-refreshes every 5 s)
- Forensic event log (HTTP probes, credential probes, honey-token hits, etc.)
- Per-IP risk score bar chart
- Blocked IP management (block/unblock from the UI)
- Honey token registry and hit history
- Live toast notifications for high-risk events

---

## Requirements

- Python 3.9 or later
- `flask>=3.0` (for the Vault dashboard)
- `mysql-connector-python>=9.3` (optional – only needed when `db_enabled: true`)

The SQLite evidence store (EvidenceStore) requires **no external database**.

---

## Quick start

```bash
# Clone the repository
git clone https://github.com/HAMMAD-4/phantom_snare.git
cd phantom_snare

# Install dependencies
pip install -r requirements.txt

# Start the HIDPS (honeypot on 2222/8080/2121, dashboard on 5000)
python main.py

# Open the dashboard in your browser
# http://127.0.0.1:5000
```

Press **Ctrl-C** to stop all modules cleanly.

---

## CLI options

```
python main.py [OPTIONS]

Options:
  --config FILE            Load configuration from a JSON file
  --ports PORT [PORT …]    Honeypot ports to listen on (overrides config)
  --bind ADDRESS           Network interface to bind to (default: 0.0.0.0)
  --log-file FILE          Write capture JSON-lines to this file
  --dashboard-port PORT    Vault dashboard port (default: 5000)
  --no-dashboard           Disable the Vault web dashboard
  --dump-config FILE       Write effective config to FILE and exit
```

### Examples

```bash
# Default run: honeypot on 2222/8080/2121, dashboard on 5000
python main.py

# Custom honeypot ports, dashboard still on 5000
python main.py --ports 22 80 443 8443

# Bind honeypot to a specific interface, disable dashboard
python main.py --ports 2222 --bind 192.168.1.1 --no-dashboard

# Use a config file (copy and edit the example)
cp config.example.json config.json
python main.py --config config.json
```

---

## Configuration

Copy `config.example.json` to `config.json` and edit as needed.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ports` | list[int] | `[2222, 8080, 2121]` | Honeypot TCP ports. |
| `bind_address` | string | `"0.0.0.0"` | Interface to bind to. |
| `max_payload_bytes` | int | `4096` | Max bytes read per connection. |
| `log_file` | string\|null | `"phantom_snare.log"` | JSON-lines log file. |
| `max_connections` | int | `50` | Listen backlog per port. |
| `banner` | string | `"Welcome\r\n"` | Text sent to connecting clients. |
| `evidence_db` | string | `"phantom_snare_evidence.db"` | SQLite evidence database path. |
| `dashboard_enabled` | bool | `true` | Enable the Vault web dashboard. |
| `dashboard_host` | string | `"127.0.0.1"` | Dashboard bind address. |
| `dashboard_port` | int | `5000` | Dashboard port. |
| `max_connections_per_minute` | int | `20` | Rate-limit threshold (Shield). |
| `db_enabled` | bool | `false` | Enable MySQL persistence. |
| `db_host` | string | `"localhost"` | MySQL host. |
| `db_port` | int | `3306` | MySQL port. |
| `db_user` | string | `"root"` | MySQL user. |
| `db_password` | string | `""` | MySQL password. |
| `db_name` | string | `"phantom_snare"` | MySQL database name. |
| `alert_email_to` | string\|null | `null` | Alert recipient email. |
| `alert_email_from` | string\|null | `null` | Alert sender email. |
| `alert_smtp_host` | string\|null | `null` | SMTP hostname. |
| `alert_smtp_port` | int | `587` | SMTP port. |
| `alert_smtp_user` | string\|null | `null` | SMTP username. |
| `alert_smtp_password` | string\|null | `null` | SMTP password. |

---

## MySQL database storage (optional)

phantom_snare can also persist captures to MySQL. This requires Laragon, WAMP,
XAMPP, or any MySQL 8+ server. The SQLite EvidenceStore works without any
external database.

### One-time setup

1. **Start MySQL** – launch Laragon (or your MySQL server).
2. **Create the database**:
   ```sql
   CREATE DATABASE IF NOT EXISTS phantom_snare
     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. **Enable in config**:
   ```json
   { "db_enabled": true, "db_host": "localhost", "db_user": "root", "db_password": "" }
   ```

---

## JSON log format

Each captured connection is written as one JSON line:

```json
{
  "timestamp": "2025-06-01T12:34:56.789012+00:00",
  "remote_ip": "203.0.113.42",
  "remote_port": 49812,
  "local_port": 2222,
  "payload_bytes": 32,
  "payload": "SSH-2.0-OpenSSH_8.9\r\n"
}
```

---

## Project structure

```
phantom_snare/
├── phantom_snare/            # Python package
│   ├── __init__.py
│   ├── config.py             # Configuration dataclass
│   ├── sqlite_db.py          # SQLite evidence store (shared by all modules)
│   ├── observer.py           # Module 1: Forensic evidence collection
│   ├── shield.py             # Module 2: IP blocking & rate limiting
│   ├── deceptor.py           # Module 3: Deceptive payloads & honey tokens
│   ├── vault.py              # Module 4: Flask web dashboard
│   ├── snare.py              # Core TCP honeypot listener
│   ├── logger.py             # CaptureRecord + JSON logging
│   ├── database.py           # MySQL persistence layer (optional)
│   ├── alerts.py             # Email alert module
│   └── templates/
│       └── dashboard.html    # Vault dashboard UI
├── tests/
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_deceptor.py
│   ├── test_logger.py
│   ├── test_observer.py
│   ├── test_shield.py
│   ├── test_snare.py
│   └── test_sqlite_db.py
├── main.py                   # CLI entry point
├── config.example.json       # Example configuration
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Dev/test dependencies
└── pyproject.toml
```

---

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## License

MIT

---

## Features

- **Multi-port listening** – deploy decoy services on any number of TCP ports simultaneously.
- **Structured JSON logging** – every captured connection is written as a JSON line (timestamp, source IP/port, payload), making it easy to ingest into Splunk, ELK, or any log aggregator.
- **MySQL persistence** – optionally save every capture to a local MySQL database (compatible with Laragon, WAMP, XAMPP). Requires `mysql-connector-python`.
- **Configurable banner** – present a realistic service banner to lure attackers into sending more data.
- **Email alerts** – optionally receive an email for every captured connection via any SMTP server.
- **Zero runtime dependencies for core features** – the honeypot listener and logging work with the Python standard library alone; `mysql-connector-python` is only needed when `db_enabled` is `true`.
- **Fully tested** – unit and integration tests covering all core modules.

---

## Requirements

- Python 3.9 or later
- No third-party runtime dependencies

---

## Installation

```bash
# Clone the repository
git clone https://github.com/HAMMAD-4/phantom_snare.git
cd phantom_snare

# (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install in editable mode (no extra packages required for runtime)
pip install -e .
```

---

## Quick start

```bash
# Listen on the default ports (2222, 8080, 2121) and log to stdout + phantom_snare.log
python main.py

# Listen on custom ports
python main.py --ports 22 80 443

# Use a config file
cp config.example.json config.json
# Edit config.json as needed, then:
python main.py --config config.json

# Bind to a specific interface
python main.py --ports 8080 --bind 192.168.1.1

# Write effective config to a file and exit
python main.py --ports 9999 --dump-config /tmp/effective.json
```

Press **Ctrl-C** to stop.

---

## Configuration

Copy `config.example.json` to `config.json` and edit as needed.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ports` | list[int] | `[2222, 8080, 2121]` | TCP ports to listen on. |
| `bind_address` | string | `"0.0.0.0"` | Network interface to bind to. |
| `max_payload_bytes` | int | `4096` | Maximum bytes to read per connection. |
| `log_file` | string\|null | `"phantom_snare.log"` | Log file path (`null` = stdout only). |
| `max_connections` | int | `50` | Listen backlog per port. |
| `banner` | string | `"Welcome\r\n"` | Text sent to connecting clients. |
| `db_enabled` | bool | `false` | Enable MySQL persistence. |
| `db_host` | string | `"localhost"` | MySQL server host (Laragon default). |
| `db_port` | int | `3306` | MySQL server port. |
| `db_user` | string | `"root"` | MySQL username (Laragon default). |
| `db_password` | string | `""` | MySQL password (Laragon default: empty). |
| `db_name` | string | `"phantom_snare"` | MySQL database name. |
| `alert_email_to` | string\|null | `null` | Recipient email for alerts. |
| `alert_email_from` | string\|null | `null` | Sender email for alerts. |
| `alert_smtp_host` | string\|null | `null` | SMTP server hostname. |
| `alert_smtp_port` | int | `587` | SMTP server port (STARTTLS). |
| `alert_smtp_user` | string\|null | `null` | SMTP username. |
| `alert_smtp_password` | string\|null | `null` | SMTP password. |

Email alerts are only sent when **all** of `alert_email_to`, `alert_email_from`, `alert_smtp_host`, `alert_smtp_user`, and `alert_smtp_password` are non-null.

---

## MySQL database storage

phantom_snare persists every captured connection to a local MySQL database (works with [Laragon](https://laragon.org/), WAMP, XAMPP, or any standard MySQL 8+ installation).

### One-time setup

1. **Start MySQL** – launch Laragon (or your local MySQL server).

2. **Create the database** – connect with a MySQL client and run:
   ```sql
   CREATE DATABASE IF NOT EXISTS phantom_snare
     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **Enable the DB in your config** – edit `config.json` (copy from `config.example.json`):
   ```json
   {
     "db_enabled": true,
     "db_host": "localhost",
     "db_port": 3306,
     "db_user": "root",
     "db_password": "",
     "db_name": "phantom_snare"
   }
   ```
   Laragon's default MySQL credentials are `root` / *(empty password)*.

4. **Install the driver**:
   ```bash
   pip install -r requirements.txt
   ```

phantom_snare automatically creates the `captures` table on first run.

### Schema

```sql
CREATE TABLE captures (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    timestamp     DATETIME(6)       NOT NULL,  -- UTC connection time
    remote_ip     VARCHAR(45)       NOT NULL,  -- IPv4 or IPv6
    remote_port   SMALLINT UNSIGNED NOT NULL,
    local_port    SMALLINT UNSIGNED NOT NULL,
    payload_bytes INT UNSIGNED      NOT NULL,
    payload       MEDIUMTEXT,                  -- UTF-8 decoded payload
    created_at    TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Querying captures

```sql
-- Most recent 20 attempts
SELECT timestamp, remote_ip, remote_port, local_port, payload
FROM captures
ORDER BY timestamp DESC
LIMIT 20;

-- All hits on port 22
SELECT * FROM captures WHERE local_port = 22;

-- Unique attackers in the last 24 hours
SELECT DISTINCT remote_ip
FROM captures
WHERE timestamp >= NOW() - INTERVAL 1 DAY;
```

---



Each captured connection produces one JSON line in the log:

```json
{
  "timestamp": "2025-06-01T12:34:56.789012+00:00",
  "remote_ip": "203.0.113.42",
  "remote_port": 49812,
  "local_port": 2222,
  "payload_bytes": 32,
  "payload": "SSH-2.0-OpenSSH_8.9\r\n"
}
```

---

## Project structure

```
phantom_snare/
├── phantom_snare/        # Python package
│   ├── __init__.py
│   ├── config.py         # Configuration dataclass
│   ├── database.py       # MySQL persistence layer
│   ├── logger.py         # CaptureRecord + logging helpers
│   ├── snare.py          # Core TCP honeypot listener
│   └── alerts.py         # Email alert module
├── tests/
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_logger.py
│   └── test_snare.py
├── main.py               # CLI entry point
├── config.example.json   # Example configuration
├── requirements.txt      # Runtime deps (mysql-connector-python)
├── requirements-dev.txt  # Dev/test deps
└── pyproject.toml
```

---

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## License

MIT
