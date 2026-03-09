import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';

import '../models/security_alert.dart';
import '../models/spoofing_event.dart';
import '../models/module_status.dart';

/// The Phantom Snare – Signal & GPS Spoofing module.
///
/// When a malicious app or external RF scanner attempts to locate the device,
/// the Snare feeds it "phantom" coordinates and simulated signal noise,
/// masking the device's true physical location.
class PhantomSnareService extends ChangeNotifier {
  final ModuleStatus status = ModuleStatus(
    id: 'phantom_snare',
    name: 'Phantom Snare',
    description: 'GPS coordinate spoofing & RF signal noise injection',
  );

  final List<SpoofingEvent> _spoofingEvents = [];
  final List<SecurityAlert> _alerts = [];
  Timer? _snareTimer;
  final _rng = Random();

  // Simulated real device location (kept secret from attackers)
  final double _realLat = 37.7749;
  final double _realLon = -122.4194;

  bool _gpsSnareActive = true;
  bool _rfSnareActive = true;
  bool _cellTowerSnareActive = false;
  bool _wifiProbeSnareActive = true;

  // Current phantom coordinates being served to attackers
  double _phantomLat = 51.5074;
  double _phantomLon = -0.1278;

  List<SpoofingEvent> get spoofingEvents => List.unmodifiable(_spoofingEvents);
  List<SecurityAlert> get alerts => List.unmodifiable(_alerts);
  bool get isActive => status.isActive;

  bool get gpsSnareActive => _gpsSnareActive;
  bool get rfSnareActive => _rfSnareActive;
  bool get cellTowerSnareActive => _cellTowerSnareActive;
  bool get wifiProbeSnareActive => _wifiProbeSnareActive;

  double get phantomLat => _phantomLat;
  double get phantomLon => _phantomLon;
  double get realLat => _realLat;
  double get realLon => _realLon;

  void activate() {
    if (status.isActive) return;
    status.isActive = true;
    _startSpoofing();
    notifyListeners();
  }

  void deactivate() {
    status.isActive = false;
    _snareTimer?.cancel();
    notifyListeners();
  }

  void setGpsSnare(bool value) {
    _gpsSnareActive = value;
    notifyListeners();
  }

  void setRfSnare(bool value) {
    _rfSnareActive = value;
    notifyListeners();
  }

  void setCellTowerSnare(bool value) {
    _cellTowerSnareActive = value;
    notifyListeners();
  }

  void setWifiProbeSnare(bool value) {
    _wifiProbeSnareActive = value;
    notifyListeners();
  }

  /// Randomize the phantom location (serves a new decoy to the attacker).
  void randomizePhantomLocation() {
    _phantomLat = (_rng.nextDouble() * 160) - 80;
    _phantomLon = (_rng.nextDouble() * 360) - 180;
    notifyListeners();
  }

  void _startSpoofing() {
    _snareTimer = Timer.periodic(const Duration(seconds: 6), (_) {
      if (!status.isActive) return;
      _simulateSpoofingEvent();
    });
  }

  void _simulateSpoofingEvent() {
    final allTypes = SpoofingType.values;
    final active = allTypes.where((t) {
      switch (t) {
        case SpoofingType.gps:
          return _gpsSnareActive;
        case SpoofingType.rfScanner:
          return _rfSnareActive;
        case SpoofingType.cellTower:
          return _cellTowerSnareActive;
        case SpoofingType.wifiProbe:
          return _wifiProbeSnareActive;
      }
    }).toList();

    if (active.isEmpty) return;

    final type = active[_rng.nextInt(active.length)];

    // Drift phantom coordinates slightly to simulate movement
    _phantomLat += (_rng.nextDouble() - 0.5) * 0.01;
    _phantomLon += (_rng.nextDouble() - 0.5) * 0.01;

    final sources = [
      'com.spyware.tracker',
      'RF-Scanner-v2',
      'com.stalkerware.loc',
      'GPS-Harvester',
      'WifiSniff-Pro',
    ];

    final event = SpoofingEvent(
      id: '${DateTime.now().millisecondsSinceEpoch}',
      realLatitude: _realLat,
      realLongitude: _realLon,
      phantomLatitude: _phantomLat,
      phantomLongitude: _phantomLon,
      triggerSource: sources[_rng.nextInt(sources.length)],
      type: type,
      timestamp: DateTime.now(),
    );

    _spoofingEvents.insert(0, event);
    if (_spoofingEvents.length > 50) {
      _spoofingEvents.removeRange(50, _spoofingEvents.length);
    }

    _alerts.insert(
      0,
      SecurityAlert(
        id: '${DateTime.now().millisecondsSinceEpoch}',
        title: '${type.label} Location Query Intercepted',
        description:
            '${event.triggerSource} attempted ${type.label} location query. '
            'Served phantom coordinates '
            '(${_phantomLat.toStringAsFixed(4)}, ${_phantomLon.toStringAsFixed(4)}) '
            'instead of real location.',
        severity: AlertSeverity.medium,
        source: AlertSource.phantomSnare,
        timestamp: DateTime.now(),
        metadata: {
          'source': event.triggerSource,
          'type': type.name,
          'phantomLat': _phantomLat,
          'phantomLon': _phantomLon,
        },
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
    _snareTimer?.cancel();
    super.dispose();
  }
}
