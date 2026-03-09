import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';

import '../models/security_alert.dart';
import '../models/network_entry.dart';
import '../models/module_status.dart';

/// The Shield – Neutralization module.
///
/// Acts as the primary firewall. Immediately severs connections to known
/// C2 (Command & Control) servers and maintains a blocklist.
class ShieldService extends ChangeNotifier {
  final ModuleStatus status = ModuleStatus(
    id: 'shield',
    name: 'The Shield',
    description: 'Firewall & C2 server neutralization engine',
  );

  // Known C2 server IPs (simulated threat intelligence feed)
  final Set<String> _blockedIPs = {
    '185.220.101.45',
    '45.142.212.100',
    '194.165.16.77',
    '91.121.87.99',
    '195.123.246.133',
    '176.107.177.39',
    '103.75.190.111',
    '23.19.58.114',
  };

  final List<NetworkEntry> _blockedConnections = [];
  final List<SecurityAlert> _alerts = [];
  Timer? _monitorTimer;
  final _rng = Random();

  int _totalBlockedConnections = 0;

  List<NetworkEntry> get blockedConnections =>
      List.unmodifiable(_blockedConnections);
  List<SecurityAlert> get alerts => List.unmodifiable(_alerts);
  Set<String> get blockedIPs => Set.unmodifiable(_blockedIPs);
  int get totalBlockedConnections => _totalBlockedConnections;
  bool get isActive => status.isActive;

  void activate() {
    if (status.isActive) return;
    status.isActive = true;
    _startMonitoring();
    notifyListeners();
  }

  void deactivate() {
    status.isActive = false;
    _monitorTimer?.cancel();
    notifyListeners();
  }

  void addToBlocklist(String ip) {
    _blockedIPs.add(ip);
    notifyListeners();
  }

  void removeFromBlocklist(String ip) {
    _blockedIPs.remove(ip);
    notifyListeners();
  }

  void _startMonitoring() {
    _monitorTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!status.isActive) return;
      _simulateBlockedConnection();
    });
  }

  void _simulateBlockedConnection() {
    final ip = _blockedIPs.elementAt(_rng.nextInt(_blockedIPs.length));
    final port = [4444, 6667, 1337, 9999, 8443][_rng.nextInt(5)];
    final protocols = ['TCP', 'UDP'];

    final entry = NetworkEntry(
      id: '${DateTime.now().millisecondsSinceEpoch}',
      sourceIp: '10.0.0.${_rng.nextInt(254) + 1}',
      destinationIp: ip,
      port: port,
      protocol: protocols[_rng.nextInt(protocols.length)],
      bytesTransferred: 0,
      timestamp: DateTime.now(),
      isMalicious: true,
      threatType: 'C2 Communication',
    );

    _blockedConnections.insert(0, entry);
    if (_blockedConnections.length > 50) {
      _blockedConnections.removeRange(50, _blockedConnections.length);
    }

    _totalBlockedConnections++;

    _alerts.insert(
      0,
      SecurityAlert(
        id: '${DateTime.now().millisecondsSinceEpoch}',
        title: 'C2 Connection Severed',
        description: 'Blocked outbound connection to known C2 server $ip:$port.',
        severity: AlertSeverity.critical,
        source: AlertSource.shield,
        timestamp: DateTime.now(),
        metadata: {'ip': ip, 'port': port},
      ),
    );

    if (_alerts.length > 50) {
      _alerts.removeRange(50, _alerts.length);
    }

    status.recordEvent(isThreat: true);
    notifyListeners();
  }

  @override
  void dispose() {
    _monitorTimer?.cancel();
    super.dispose();
  }
}
