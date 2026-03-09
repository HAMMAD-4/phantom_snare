# Testing Guide — SentinelPrivacy (Phantom Snare)

This guide explains **how to verify that the app works correctly, will not hang, and will not corrupt your phone**.

---

## Quick Start

```bash
# Install dependencies
flutter pub get

# Run ALL tests (unit + widget + stability + safety)
flutter test

# Run a specific test suite
flutter test test/sentinel_privacy_test.dart   # Unit tests (models & services)
flutter test test/stability_test.dart           # Stability & no-hang tests
flutter test test/safety_test.dart              # Safety & simulation-only tests
flutter test test/widget_test.dart              # Widget smoke tests (UI renders)
```

---

## What Each Test Suite Covers

### 1. Unit Tests (`test/sentinel_privacy_test.dart`)

Validates the core business logic:

| Area | What is tested |
|------|----------------|
| **SecurityAlert** | Severity colours, labels, acknowledgement state |
| **SuspiciousApp** | Risk score bounds (0–100), risk labels, blocking |
| **ExfiltrationAttempt** | Expansion ratios, deception labels, zero-size edge cases |
| **SpoofingEvent** | Distance calculations, coordinate validation |
| **ModuleStatus** | Event recording, counter increments |
| **All 5 Services** | Activation, deactivation, state mutations, alert caps |

### 2. Stability Tests (`test/stability_test.dart`)

Proves the app **will not hang or freeze**:

| Test group | What is verified |
|------------|-----------------|
| **Timer lifecycle** | Every service correctly creates and cancels its internal `Timer` during activate → deactivate → dispose. |
| **Rapid cycling** | 50× activate/deactivate loops complete without hanging. |
| **Double activate** | Calling `activate()` twice does not create duplicate timers. |
| **Dispose before activate** | Disposing a never-activated service is safe. |
| **Memory bounds** | Alert lists stay within defined caps (200 for Vault, 50 for others). |
| **Stress test** | 1 000 rapid alert insertions stay bounded at 200. |
| **Safe no-ops** | Blocking a non-existent app, removing a non-existent IP, acknowledging a missing alert — all complete without errors. |

### 3. Safety Tests (`test/safety_test.dart`)

Proves the app **will not corrupt your phone**:

| Test group | What is verified |
|------------|-----------------|
| **Simulation only** | All data (malicious apps, C2 IPs, GPS coordinates) comes from hardcoded constants — no real device scans. |
| **No file writes** | "Zip bombs" and "garbage strings" are purely logical counters; nothing is written to disk. |
| **No GPS access** | The "real location" is a hardcoded constant (37.7749, −122.4194); no `LocationManager` call is made. |
| **No native plugins** | All services can be created and used in a plain Dart test environment — proof that no platform channels (native code) are required. |
| **Data isolation** | Each module's state is independent; one module cannot corrupt another. |
| **Immutable getters** | Public getters return unmodifiable lists; external code cannot accidentally mutate internal state. |

### 4. Widget Tests (`test/widget_test.dart`)

Proves the **UI renders without crashing**:

| Test | What is verified |
|------|-----------------|
| **VaultScreen** | Dashboard renders title and module cards |
| **ObserverScreen** | Forensic collection screen renders |
| **ShieldScreen** | Firewall screen renders |
| **DeceptorScreen** | Data poisoning screen renders |
| **PhantomSnareScreen** | GPS spoofing screen renders |
| **SentinelPrivacyApp** | Root MaterialApp widget renders |
| **Navigation** | Module cards are visible on the dashboard |

---

## How to Test on a Real Device / Emulator

### Step 1 — Run on an Emulator First (Recommended)

```bash
# Start an Android emulator
flutter emulators --launch <emulator_name>

# Or start an iOS simulator (macOS only)
open -a Simulator

# Run the app
flutter run
```

### Step 2 — What to Check Manually

| Check | How | Expected result |
|-------|-----|-----------------|
| **App launches** | Open the app | Dashboard loads within 2–3 seconds with all module cards visible |
| **No crashes** | Navigate to every screen | Each screen (Observer, Shield, Deceptor, Phantom Snare) opens without errors |
| **Live alerts appear** | Wait 10–15 seconds on the dashboard | Alert feed populates with simulated threat events |
| **Toggles work** | Tap module on/off switches | Modules activate/deactivate; green indicator appears/disappears |
| **No freezing** | Use the app for 5+ minutes | UI stays responsive; scrolling is smooth |
| **Memory stable** | Run for 10+ minutes | App does not slow down (lists are capped at 50–200 entries) |
| **Back navigation** | Press back from sub-screens | Returns to dashboard without errors |
| **Forensic report** | Tap the report button on the Vault screen | Report dialog opens with alert history |
| **Randomise location** | On Phantom Snare screen, tap "Randomise" | Phantom coordinates change |

### Step 3 — Performance Profiling

```bash
# Run in profile mode to check for jank/frame drops
flutter run --profile

# Open DevTools for detailed performance analysis
flutter pub global activate devtools
flutter pub global run devtools
```

In **DevTools → Performance** tab:
- Verify frame render times are under 16 ms (60 fps target)
- Check that no timer callbacks cause UI thread blocking

### Step 4 — Static Analysis

```bash
# Run Dart linter to catch potential issues
flutter analyze
```

All rules from `analysis_options.yaml` must pass.

---

## Why This App Is Safe for Your Phone

| Concern | Answer |
|---------|--------|
| **Will it access my contacts?** | **No.** The "suspicious apps" list is hardcoded data. The app never calls any system API to read contacts, SMS, call logs, or photos. |
| **Will it access my GPS?** | **No.** The "real location" is a hardcoded constant (San Francisco). No `LocationManager` or platform channel is used. |
| **Will it make network requests?** | **No.** The "blocked C2 IPs" are simulated. No actual HTTP/socket connections are created. |
| **Will it write large files (Zip Bombs)?** | **No.** The "Zip Bomb" feature only tracks *byte counts* in memory. No actual compressed files are created on disk. |
| **Will it drain my battery?** | **Minimal.** The app uses lightweight `Timer.periodic` callbacks (3–6 second intervals) that update in-memory lists. There are no background services, wake locks, or persistent processes. |
| **Will it run in the background?** | **No.** When you close the app, all Dart timers are automatically cancelled. The app has no background service, no foreground notification, and no `WorkManager` task. |
| **Can it brick my phone?** | **No.** The app requires no special permissions (no root, no device admin, no accessibility service). It cannot modify system settings, other apps, or device firmware. |

---

## Continuous Integration

To set up automated testing in CI (e.g., GitHub Actions):

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.24.x'
      - run: flutter pub get
      - run: flutter analyze
      - run: flutter test
```

---

## Summary

| Command | Purpose |
|---------|---------|
| `flutter test` | Run all automated tests |
| `flutter analyze` | Check for lint errors and potential bugs |
| `flutter run` | Run on a connected device / emulator |
| `flutter run --profile` | Run with performance profiling |
| `flutter test --coverage` | Generate code coverage report |
