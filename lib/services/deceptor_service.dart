import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';

import '../models/security_alert.dart';
import '../models/exfiltration_attempt.dart';
import '../models/module_status.dart';

/// The Deceptor – Data Poisoning module.
///
/// Intercepts data exfiltration attempts and replaces real data with
/// Zip Bombs, malformed metadata, or garbage strings. Corrupts the
/// attacker's database and renders stolen information useless.
class DeceptorService extends ChangeNotifier {
  final ModuleStatus status = ModuleStatus(
    id: 'deceptor',
    name: 'The Deceptor',
    description: 'Data poisoning via Zip Bombs, garbage injection & phantom data',
  );

  final List<ExfiltrationAttempt> _interceptedAttempts = [];
  final List<SecurityAlert> _alerts = [];
  Timer? _deceptionTimer;
  final _rng = Random();

  int _totalBytesPoison = 0;
  int _totalDataSaved = 0;

  List<ExfiltrationAttempt> get interceptedAttempts =>
      List.unmodifiable(_interceptedAttempts);
  List<SecurityAlert> get alerts => List.unmodifiable(_alerts);
  int get totalBytesPoison => _totalBytesPoison;
  int get totalDataSaved => _totalDataSaved;
  bool get isActive => status.isActive;

  static const _dataTypes = [
    'Contact List',
    'SMS Messages',
    'Call History',
    'GPS History',
    'Photos Metadata',
    'Browser History',
    'Clipboard Content',
    'App Credentials',
  ];

  static const _methods = [
    'zip_bomb',
    'garbage_strings',
    'malformed_metadata',
    'phantom_contacts',
    'fake_location',
  ];

  static const _appNames = [
    'Calculator Pro',
    'Super Flashlight',
    'FreeVPN Lite',
    'Game Runner',
    'Weather Now',
  ];

  void activate() {
    if (status.isActive) return;
    status.isActive = true;
    _startDeception();
    notifyListeners();
  }

  void deactivate() {
    status.isActive = false;
    _deceptionTimer?.cancel();
    notifyListeners();
  }

  void _startDeception() {
    _deceptionTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!status.isActive) return;
      _simulateInterception();
    });
  }

  void _simulateInterception() {
    final dataType = _dataTypes[_rng.nextInt(_dataTypes.length)];
    final method = _methods[_rng.nextInt(_methods.length)];
    final appName = _appNames[_rng.nextInt(_appNames.length)];
    final originalSize = _rng.nextInt(10000) + 1000;

    // Zip bombs expand massively; other methods still inflate the payload
    final int poisonSize;
    if (method == 'zip_bomb') {
      poisonSize = originalSize * (_rng.nextInt(500) + 200);
    } else {
      poisonSize = originalSize * (_rng.nextInt(10) + 2);
    }

    final attempt = ExfiltrationAttempt(
      id: '${DateTime.now().millisecondsSinceEpoch}',
      appName: appName,
      dataType: dataType,
      originalDataSizeBytes: originalSize,
      poisonedDataSizeBytes: poisonSize,
      deceptionMethod: method,
      timestamp: DateTime.now(),
    );

    _interceptedAttempts.insert(0, attempt);
    if (_interceptedAttempts.length > 50) {
      _interceptedAttempts.removeRange(50, _interceptedAttempts.length);
    }

    _totalBytesPoison += poisonSize;
    _totalDataSaved += originalSize;

    _alerts.insert(
      0,
      SecurityAlert(
        id: '${DateTime.now().millisecondsSinceEpoch}',
        title: 'Exfiltration Poisoned: $dataType',
        description:
            '$appName attempted to exfiltrate $dataType. '
            'Replaced with ${attempt.deceptionLabel} '
            '(${_formatBytes(originalSize)} → ${_formatBytes(poisonSize)}).',
        severity: AlertSeverity.high,
        source: AlertSource.deceptor,
        timestamp: DateTime.now(),
        metadata: {
          'app': appName,
          'dataType': dataType,
          'method': method,
          'originalSize': originalSize,
          'poisonSize': poisonSize,
        },
      ),
    );

    if (_alerts.length > 50) {
      _alerts.removeRange(50, _alerts.length);
    }

    status.recordEvent(isThreat: true);
    notifyListeners();
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  void dispose() {
    _deceptionTimer?.cancel();
    super.dispose();
  }
}
