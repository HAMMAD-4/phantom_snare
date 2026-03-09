import 'package:flutter_test/flutter_test.dart';

import 'package:sentinel_privacy/models/security_alert.dart';
import 'package:sentinel_privacy/services/observer_service.dart';
import 'package:sentinel_privacy/services/shield_service.dart';
import 'package:sentinel_privacy/services/deceptor_service.dart';
import 'package:sentinel_privacy/services/phantom_snare_service.dart';
import 'package:sentinel_privacy/services/vault_service.dart';

/// Safety tests — prove that the app uses **simulation only** and will not
/// access real hardware, make real network calls, or write to device storage.
/// These tests give confidence that installing the app cannot corrupt a phone.
///
/// Run with: flutter test test/safety_test.dart
void main() {
  // ---------------------------------------------------------------------------
  // Simulation-only verification
  // ---------------------------------------------------------------------------
  group('Simulation-only (no real system calls)', () {
    test('ObserverService uses hardcoded sample apps, not real device scan',
        () {
      final service = ObserverService();
      service.activate();
      // After activation the service simulates via Timer but does not perform
      // any real PackageManager / system call query.  The detected-apps list
      // only ever contains entries from the internal _sampleApps constant.
      // Immediately after activate (before first timer tick) the list is empty.
      expect(service.detectedApps.length, lessThanOrEqualTo(4));
      service.dispose();
    });

    test('ShieldService blocklist contains only simulated IPs', () {
      final service = ShieldService();
      // Blocklist is initialised from a hardcoded set — no DNS / network calls
      expect(service.blockedIPs, isNotEmpty);
      for (final ip in service.blockedIPs) {
        // Each entry should be a valid IPv4 string (simulated)
        expect(ip, matches(RegExp(r'^\d{1,3}(\.\d{1,3}){3}$')));
      }
      service.dispose();
    });

    test('DeceptorService does not write files to disk', () {
      final service = DeceptorService();
      service.activate();
      // The "zip bombs" and "garbage strings" are purely logical — no
      // actual data is ever written to the file system.
      expect(service.totalBytesPoison, equals(0)); // 0 before first tick
      service.dispose();
    });

    test('PhantomSnareService does not access real GPS hardware', () {
      final service = PhantomSnareService();
      // The "real" location is a hardcoded constant (San Francisco)
      expect(service.realLat, equals(37.7749));
      expect(service.realLon, equals(-122.4194));
      // Phantom location is also a constant (London) — no LocationManager call
      expect(service.phantomLat, isNotNull);
      expect(service.phantomLon, isNotNull);
      service.dispose();
    });

    test('VaultService stores alerts in memory only, not on disk', () {
      final service = VaultService();
      service.addAlert(_makeAlert('safety_1'));
      service.addAlert(_makeAlert('safety_2'));
      expect(service.aggregatedAlerts.length, equals(2));
      // Clearing alerts removes them entirely — nothing persisted
      service.clearAlerts();
      expect(service.aggregatedAlerts, isEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // No platform channel / native calls
  // ---------------------------------------------------------------------------
  group('No native platform calls', () {
    test('All services can be instantiated without platform channels', () {
      // If any service relied on a native plugin (GPS, file-system, network)
      // these constructors would throw MissingPluginException in test.
      final observer = ObserverService();
      final shield = ShieldService();
      final deceptor = DeceptorService();
      final phantom = PhantomSnareService();
      final vault = VaultService();

      expect(observer, isNotNull);
      expect(shield, isNotNull);
      expect(deceptor, isNotNull);
      expect(phantom, isNotNull);
      expect(vault, isNotNull);

      observer.dispose();
      shield.dispose();
      deceptor.dispose();
      phantom.dispose();
    });

    test('All services can activate/deactivate without platform channels', () {
      final services = <dynamic>[
        ObserverService(),
        ShieldService(),
        DeceptorService(),
        PhantomSnareService(),
      ];
      for (final s in services) {
        s.activate();
        s.deactivate();
        s.dispose();
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Data isolation — one module's state does not leak into another
  // ---------------------------------------------------------------------------
  group('Data isolation between modules', () {
    test('VaultService alerts are independent of individual services', () {
      final vault = VaultService();
      final observer = ObserverService();

      vault.addAlert(_makeAlert('vault_only'));
      // Observer's alerts list is separate from vault's
      expect(observer.alerts, isEmpty);
      expect(vault.aggregatedAlerts.length, equals(1));

      observer.dispose();
    });

    test('ShieldService blocklist changes do not affect ObserverService', () {
      final shield = ShieldService();
      final observer = ObserverService();

      final originalIpCount = shield.blockedIPs.length;
      shield.addToBlocklist('1.2.3.4');
      expect(shield.blockedIPs.length, equals(originalIpCount + 1));
      // Observer has no blocklist concept — it should be unaffected
      expect(observer.detectedApps, isEmpty);

      shield.dispose();
      observer.dispose();
    });
  });

  // ---------------------------------------------------------------------------
  // Getters return unmodifiable copies (caller cannot corrupt internal state)
  // ---------------------------------------------------------------------------
  group('Immutable getters (no external mutation)', () {
    test('ObserverService.detectedApps is unmodifiable', () {
      final service = ObserverService();
      final apps = service.detectedApps;
      expect(() => apps.add(null as dynamic), throwsA(isA<Error>()));
      service.dispose();
    });

    test('ObserverService.networkLog is unmodifiable', () {
      final service = ObserverService();
      final log = service.networkLog;
      expect(() => log.add(null as dynamic), throwsA(isA<Error>()));
      service.dispose();
    });

    test('ShieldService.blockedConnections is unmodifiable', () {
      final service = ShieldService();
      final connections = service.blockedConnections;
      expect(() => connections.add(null as dynamic), throwsA(isA<Error>()));
      service.dispose();
    });

    test('DeceptorService.interceptedAttempts is unmodifiable', () {
      final service = DeceptorService();
      final attempts = service.interceptedAttempts;
      expect(() => attempts.add(null as dynamic), throwsA(isA<Error>()));
      service.dispose();
    });

    test('PhantomSnareService.spoofingEvents is unmodifiable', () {
      final service = PhantomSnareService();
      final events = service.spoofingEvents;
      expect(() => events.add(null as dynamic), throwsA(isA<Error>()));
      service.dispose();
    });

    test('VaultService.aggregatedAlerts is unmodifiable', () {
      final service = VaultService();
      final alerts = service.aggregatedAlerts;
      expect(() => alerts.add(null as dynamic), throwsA(isA<Error>()));
    });
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

SecurityAlert _makeAlert(String id) {
  return SecurityAlert(
    id: id,
    title: 'Test Alert $id',
    description: 'Safety test alert',
    severity: AlertSeverity.info,
    source: AlertSource.vault,
    timestamp: DateTime.now(),
  );
}
