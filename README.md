# SentinelPrivacy (Phantom Snare)

**An AI-Powered HIDPS with Dynamic Deception and Signal Spoofing**

A Flutter mobile application implementing a Host-based Intrusion Detection and Prevention System (HIDPS) that uses dynamic deception to "snare" attackers by feeding them corrupted, malformed, or "phantom" data.

---

## Architecture

The system is divided into five specialized modules:

| Module | Function |
|---|---|
| **The Observer** | Forensic collection via system call monitoring & local loopback VPN hooks. Identifies data-stealing patterns (e.g., offline apps requesting contact list access). |
| **The Shield** | Primary firewall. Severs connections to known C2 (Command & Control) servers and maintains a dynamic blocklist. |
| **The Deceptor** | Intercepts data exfiltration attempts and replaces real data with Zip Bombs, malformed metadata, or garbage strings. |
| **The Phantom Snare** | Targets RF hacking and GPS tracking. Feeds "phantom" coordinates and simulated signal noise to mask the device's true location. |
| **The Vault** | Command center dashboard with real-time alerts, module status, and forensic evidence report generation. |

---

## Tech Stack

- **Framework**: Flutter (Dart)
- **State Management**: Provider
- **UI**: Material 3, Google Fonts (Orbitron + Source Code Pro)
- **Charts**: fl_chart

---

## Getting Started

### Prerequisites

- Flutter SDK ≥ 3.0.0
- Dart SDK ≥ 3.0.0

### Installation

```bash
flutter pub get
flutter run
```

### Running Tests

```bash
flutter test
```

---

## Features

- **Active Counter-Offensive**: Doesn't just block — actively wastes attacker resources via data inflation (Zip Bombs up to 500× expansion).
- **Agentic Intelligence**: Autonomous module decisions on which "phantom" data to serve based on attack type.
- **Signal Masking**: Addresses GPS/RF hardware-level threats ignored by standard mobile AVs.
- **Forensic Reporting**: Generates detailed evidence reports for all intercepted events.
- **Real-time Dashboard**: Live alert feed aggregated across all modules.

---

## Security Notes

This application is a **simulation/demonstration** of HIDPS concepts. Actual system call monitoring, VPN hooking, and GPS spoofing require elevated OS permissions and platform-specific native code beyond the scope of this Flutter UI layer.