import 'package:flutter/foundation.dart';

import '../models/security_alert.dart';
import '../models/module_status.dart';

/// The Vault – Command Center service.
///
/// Aggregates alerts and stats from all modules and provides the
/// forensic evidence summary for export.
class VaultService extends ChangeNotifier {
  final ModuleStatus status = ModuleStatus(
    id: 'vault',
    name: 'The Vault',
    description: 'Real-time command center & forensic evidence aggregator',
    isActive: true,
  );

  final List<SecurityAlert> _aggregatedAlerts = [];
  int _selectedTabIndex = 0;

  List<SecurityAlert> get aggregatedAlerts =>
      List.unmodifiable(_aggregatedAlerts);
  int get selectedTabIndex => _selectedTabIndex;

  // Maximum number of alerts retained in memory.
  static const int _maxAlerts = 200;

  void addAlert(SecurityAlert alert) {
    _aggregatedAlerts.insert(0, alert);
    if (_aggregatedAlerts.length > _maxAlerts) {
      _aggregatedAlerts.removeRange(_maxAlerts, _aggregatedAlerts.length);
    }
    notifyListeners();
  }

  void acknowledgeAlert(String alertId) {
    final idx = _aggregatedAlerts.indexWhere((a) => a.id == alertId);
    if (idx >= 0) {
      _aggregatedAlerts[idx].isAcknowledged = true;
      notifyListeners();
    }
  }

  void clearAlerts() {
    _aggregatedAlerts.clear();
    notifyListeners();
  }

  void setSelectedTab(int index) {
    _selectedTabIndex = index;
    notifyListeners();
  }

  int get unacknowledgedCount =>
      _aggregatedAlerts.where((a) => !a.isAcknowledged).length;

  int get criticalCount => _aggregatedAlerts
      .where((a) => a.severity == AlertSeverity.critical)
      .length;

  /// Returns a formatted forensic report string for all aggregated alerts.
  String generateForensicReport() {
    final buf = StringBuffer();
    buf.writeln('=== SentinelPrivacy Forensic Report ===');
    buf.writeln('Generated: ${DateTime.now().toIso8601String()}');
    buf.writeln('Total Events: ${_aggregatedAlerts.length}');
    buf.writeln('');
    for (final alert in _aggregatedAlerts) {
      buf.writeln('[${alert.severityLabel}] ${alert.timestamp.toIso8601String()}');
      buf.writeln('  Source  : ${alert.sourceLabel}');
      buf.writeln('  Title   : ${alert.title}');
      buf.writeln('  Detail  : ${alert.description}');
      buf.writeln('');
    }
    return buf.toString();
  }
}
