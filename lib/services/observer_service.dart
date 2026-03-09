import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';

import '../models/security_alert.dart';
import '../models/suspicious_app.dart';
import '../models/network_entry.dart';
import '../models/module_status.dart';

/// The Observer – Forensic Collection module.
///
/// Monitors system calls, API hooks, and network traffic.
/// Identifies data-stealing patterns (e.g., offline apps requesting sensitive
/// permissions) and emits [SecurityAlert]s for the Vault.
class ObserverService extends ChangeNotifier {
  final ModuleStatus status = ModuleStatus(
    id: 'observer',
    name: 'The Observer',
    description: 'Forensic collection via system call monitoring & VPN hooks',
  );

  final List<SuspiciousApp> _detectedApps = [];
  final List<NetworkEntry> _networkLog = [];
  final List<SecurityAlert> _alerts = [];
  Timer? _scanTimer;
  final _rng = Random();

  List<SuspiciousApp> get detectedApps => List.unmodifiable(_detectedApps);
  List<NetworkEntry> get networkLog => List.unmodifiable(_networkLog);
  List<SecurityAlert> get alerts => List.unmodifiable(_alerts);

  bool get isActive => status.isActive;

  // Simulated known malicious apps/patterns for demonstration
  static const _sampleApps = [
    ('com.offline.calculator', 'Calculator Pro',
        ['READ_CONTACTS', 'ACCESS_FINE_LOCATION', 'READ_SMS'],
        ['Contacts exfil', 'Background GPS polling']),
    ('com.flashlight.app', 'Super Flashlight',
        ['RECORD_AUDIO', 'READ_CALL_LOG'],
        ['Microphone tap detected']),
    ('com.freeVPN.lite', 'FreeVPN Lite',
        ['READ_CONTACTS', 'READ_EXTERNAL_STORAGE'],
        ['Data tunneling to C2', 'Clipboard sniffing']),
    ('com.game.runner', 'Game Runner',
        ['ACCESS_FINE_LOCATION', 'CAMERA'],
        ['Hidden location transmitter']),
  ];

  void activate() {
    if (status.isActive) return;
    status.isActive = true;
    _startSimulation();
    notifyListeners();
  }

  void deactivate() {
    status.isActive = false;
    _scanTimer?.cancel();
    notifyListeners();
  }

  void _startSimulation() {
    // Simulate periodic discovery of suspicious apps and network events.
    _scanTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!status.isActive) return;
      _simulateScan();
    });
  }

  void _simulateScan() {
    final idx = _rng.nextInt(_sampleApps.length);
    final (pkg, name, perms, behaviors) = _sampleApps[idx];

    final existing = _detectedApps.indexWhere((a) => a.packageName == pkg);
    if (existing >= 0) {
      _detectedApps[existing].accessAttempts++;
    } else {
      _detectedApps.add(SuspiciousApp(
        packageName: pkg,
        appName: name,
        suspiciousPermissions: perms,
        detectedBehaviors: behaviors,
        firstDetected: DateTime.now(),
        accessAttempts: 1,
      ));
    }

    // Generate a network entry
    _networkLog.insert(
      0,
      NetworkEntry(
        id: '${DateTime.now().millisecondsSinceEpoch}',
        sourceIp: '192.168.1.${_rng.nextInt(254) + 1}',
        destinationIp:
            '${_rng.nextInt(220) + 10}.${_rng.nextInt(255)}.${_rng.nextInt(255)}.${_rng.nextInt(254) + 1}',
        port: [80, 443, 8080, 4444, 1337][_rng.nextInt(5)],
        protocol: ['TCP', 'UDP', 'HTTPS'][_rng.nextInt(3)],
        bytesTransferred: _rng.nextInt(50000) + 100,
        timestamp: DateTime.now(),
        isMalicious: _rng.nextBool(),
        threatType: _rng.nextBool() ? 'Data Exfiltration' : null,
      ),
    );

    if (_networkLog.length > 100) {
      _networkLog.removeRange(100, _networkLog.length);
    }

    // Emit alert for suspicious apps
    _alerts.insert(
      0,
      SecurityAlert(
        id: '${DateTime.now().millisecondsSinceEpoch}',
        title: 'Suspicious Activity: $name',
        description:
            'App $pkg is accessing: ${perms.join(", ")}. '
            'Behaviors: ${behaviors.join(", ")}.',
        severity: AlertSeverity.high,
        source: AlertSource.observer,
        timestamp: DateTime.now(),
        metadata: {'package': pkg, 'permissions': perms},
      ),
    );

    if (_alerts.length > 50) {
      _alerts.removeRange(50, _alerts.length);
    }

    status.recordEvent(isThreat: true);
    notifyListeners();
  }

  /// Block a specific app by package name.
  void blockApp(String packageName) {
    final idx = _detectedApps.indexWhere((a) => a.packageName == packageName);
    if (idx >= 0) {
      _detectedApps[idx].isBlocked = true;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _scanTimer?.cancel();
    super.dispose();
  }
}
