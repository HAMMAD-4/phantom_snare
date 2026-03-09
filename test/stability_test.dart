import 'package:flutter_test/flutter_test.dart';

import 'package:sentinel_privacy/services/observer_service.dart';
import 'package:sentinel_privacy/services/shield_service.dart';
import 'package:sentinel_privacy/services/deceptor_service.dart';
import 'package:sentinel_privacy/services/phantom_snare_service.dart';
import 'package:sentinel_privacy/services/vault_service.dart';
import 'package:sentinel_privacy/models/security_alert.dart';

/// Stability tests — verify that the app will not hang, leak memory, or
/// misbehave during normal usage.
///
/// Run with: flutter test test/stability_test.dart
void main() {
  // ---------------------------------------------------------------------------
  // Timer lifecycle: activate → deactivate → dispose must not leak timers
  // ---------------------------------------------------------------------------
  group('Timer lifecycle (no hangs)', () {
    test('ObserverService: activate then dispose cancels timer cleanly', () {
      final service = ObserverService();
      service.activate();
      expect(service.isActive, isTrue);
      // dispose should cancel internal timer without error
      service.dispose();
    });

    test('ShieldService: activate then dispose cancels timer cleanly', () {
      final service = ShieldService();
      service.activate();
      expect(service.isActive, isTrue);
      service.dispose();
    });

    test('DeceptorService: activate then dispose cancels timer cleanly', () {
      final service = DeceptorService();
      service.activate();
      expect(service.isActive, isTrue);
      service.dispose();
    });

    test('PhantomSnareService: activate then dispose cancels timer cleanly',
        () {
      final service = PhantomSnareService();
      service.activate();
      expect(service.isActive, isTrue);
      service.dispose();
    });

    test('ObserverService: repeated activate/deactivate cycles are safe', () {
      final service = ObserverService();
      for (int i = 0; i < 50; i++) {
        service.activate();
        service.deactivate();
      }
      // Should reach here without hanging or throwing
      expect(service.isActive, isFalse);
      service.dispose();
    });

    test('ShieldService: repeated activate/deactivate cycles are safe', () {
      final service = ShieldService();
      for (int i = 0; i < 50; i++) {
        service.activate();
        service.deactivate();
      }
      expect(service.isActive, isFalse);
      service.dispose();
    });

    test('DeceptorService: repeated activate/deactivate cycles are safe', () {
      final service = DeceptorService();
      for (int i = 0; i < 50; i++) {
        service.activate();
        service.deactivate();
      }
      expect(service.isActive, isFalse);
      service.dispose();
    });

    test('PhantomSnareService: repeated activate/deactivate cycles are safe',
        () {
      final service = PhantomSnareService();
      for (int i = 0; i < 50; i++) {
        service.activate();
        service.deactivate();
      }
      expect(service.isActive, isFalse);
      service.dispose();
    });

    test('Double-activate does not create duplicate timers', () {
      final service = ObserverService();
      service.activate();
      service.activate(); // second call should be a no-op
      expect(service.isActive, isTrue);
      service.dispose();
    });

    test('Deactivate before activate is safe', () {
      final service = ShieldService();
      service.deactivate(); // no-op when already inactive
      expect(service.isActive, isFalse);
      service.dispose();
    });

    test('Dispose before activate is safe', () {
      final service = DeceptorService();
      service.dispose(); // disposing a never-activated service should be fine
    });
  });

  // ---------------------------------------------------------------------------
  // Memory bounds: lists must stay within defined caps
  // ---------------------------------------------------------------------------
  group('Memory bounds (no unbounded growth)', () {
    test('VaultService caps alerts at 200', () {
      final service = VaultService();
      for (int i = 0; i < 300; i++) {
        service.addAlert(SecurityAlert(
          id: 'alert_$i',
          title: 'Test $i',
          description: 'Description $i',
          severity: AlertSeverity.info,
          source: AlertSource.vault,
          timestamp: DateTime.now(),
        ));
      }
      expect(service.aggregatedAlerts.length, lessThanOrEqualTo(200));
    });

    test('VaultService: rapid alert additions stay bounded', () {
      final service = VaultService();
      // Simulate burst of 1000 alerts (stress test)
      for (int i = 0; i < 1000; i++) {
        service.addAlert(SecurityAlert(
          id: 'burst_$i',
          title: 'Burst $i',
          description: 'Burst description',
          severity: AlertSeverity.high,
          source: AlertSource.observer,
          timestamp: DateTime.now(),
        ));
      }
      expect(service.aggregatedAlerts.length, lessThanOrEqualTo(200));
    });

    test('ObserverService: detectedApps list is bounded to sample set', () {
      final service = ObserverService();
      // The service only detects from a fixed set of 4 sample apps
      // so detectedApps should never exceed the sample count
      service.activate();
      service.deactivate();
      expect(service.detectedApps.length, lessThanOrEqualTo(4));
      service.dispose();
    });

    test('VaultService clearAlerts frees memory', () {
      final service = VaultService();
      for (int i = 0; i < 200; i++) {
        service.addAlert(SecurityAlert(
          id: 'mem_$i',
          title: 'Memory test $i',
          description: 'Testing memory',
          severity: AlertSeverity.low,
          source: AlertSource.vault,
          timestamp: DateTime.now(),
        ));
      }
      expect(service.aggregatedAlerts, isNotEmpty);
      service.clearAlerts();
      expect(service.aggregatedAlerts, isEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // State consistency after operations
  // ---------------------------------------------------------------------------
  group('State consistency', () {
    test('ObserverService: blockApp does not crash on empty list', () {
      final service = ObserverService();
      // Calling blockApp when no apps detected should not throw
      service.blockApp('com.nonexistent.app');
      service.dispose();
    });

    test('ShieldService: removeFromBlocklist for non-existent IP is safe', () {
      final service = ShieldService();
      service.removeFromBlocklist('999.999.999.999');
      // Should not throw
      expect(service.blockedIPs, isNotEmpty);
      service.dispose();
    });

    test('VaultService: acknowledgeAlert for non-existent ID is safe', () {
      final service = VaultService();
      service.acknowledgeAlert('non_existent_id');
      // Should not throw
      expect(service.aggregatedAlerts, isEmpty);
    });

    test('PhantomSnareService: toggle snares when inactive is safe', () {
      final service = PhantomSnareService();
      service.setGpsSnare(false);
      service.setRfSnare(false);
      service.setCellTowerSnare(true);
      service.setWifiProbeSnare(false);
      // All toggles should work without activating the service
      expect(service.gpsSnareActive, isFalse);
      expect(service.rfSnareActive, isFalse);
      expect(service.cellTowerSnareActive, isTrue);
      expect(service.wifiProbeSnareActive, isFalse);
      service.dispose();
    });

    test('PhantomSnareService: randomize produces valid coordinates', () {
      final service = PhantomSnareService();
      for (int i = 0; i < 100; i++) {
        service.randomizePhantomLocation();
        expect(service.phantomLat, inInclusiveRange(-90.0, 90.0));
        expect(service.phantomLon, inInclusiveRange(-180.0, 180.0));
      }
      service.dispose();
    });

    test('VaultService: forensic report on empty alerts does not crash', () {
      final service = VaultService();
      final report = service.generateForensicReport();
      expect(report, contains('SentinelPrivacy'));
      expect(report, contains('Total Events: 0'));
    });
  });
}
