import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:sentinel_privacy/app.dart';
import 'package:sentinel_privacy/services/observer_service.dart';
import 'package:sentinel_privacy/services/shield_service.dart';
import 'package:sentinel_privacy/services/deceptor_service.dart';
import 'package:sentinel_privacy/services/phantom_snare_service.dart';
import 'package:sentinel_privacy/services/vault_service.dart';
import 'package:sentinel_privacy/screens/vault_screen.dart';
import 'package:sentinel_privacy/screens/observer_screen.dart';
import 'package:sentinel_privacy/screens/shield_screen.dart';
import 'package:sentinel_privacy/screens/deceptor_screen.dart';
import 'package:sentinel_privacy/screens/phantom_snare_screen.dart';

/// Widget smoke tests — verify that every screen can render without crashing.
/// These tests catch missing assets, null errors, and layout overflow issues.
///
/// Run with: flutter test test/widget_test.dart

/// Duration to wait after pumping a widget tree before assertions.
const _settleTimeout = Duration(seconds: 1);

void main() {
  /// Helper that wraps a widget with the full Provider tree so that
  /// Consumer<…> look-ups succeed during the test pump.
  Widget _wrapWithProviders(Widget child) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ObserverService()),
        ChangeNotifierProvider(create: (_) => ShieldService()),
        ChangeNotifierProvider(create: (_) => DeceptorService()),
        ChangeNotifierProvider(create: (_) => PhantomSnareService()),
        ChangeNotifierProvider(create: (_) => VaultService()),
      ],
      child: MaterialApp(home: child),
    );
  }

  group('Screen smoke tests (app renders without crashing)', () {
    testWidgets('VaultScreen renders title and module cards',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const VaultScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      // The dashboard should show the app name
      expect(find.textContaining('Sentinel'), findsWidgets);
    });

    testWidgets('ObserverScreen renders without errors',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const ObserverScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      expect(find.textContaining('Observer'), findsWidgets);
    });

    testWidgets('ShieldScreen renders without errors',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const ShieldScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      expect(find.textContaining('Shield'), findsWidgets);
    });

    testWidgets('DeceptorScreen renders without errors',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const DeceptorScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      expect(find.textContaining('Deceptor'), findsWidgets);
    });

    testWidgets('PhantomSnareScreen renders without errors',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const PhantomSnareScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      expect(find.textContaining('Phantom'), findsWidgets);
    });

    testWidgets('SentinelPrivacyApp root widget renders',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => ObserverService()),
            ChangeNotifierProvider(create: (_) => ShieldService()),
            ChangeNotifierProvider(create: (_) => DeceptorService()),
            ChangeNotifierProvider(create: (_) => PhantomSnareService()),
            ChangeNotifierProvider(create: (_) => VaultService()),
          ],
          child: const SentinelPrivacyApp(),
        ),
      );
      await tester.pumpAndSettle(_settleTimeout);

      // The app should display without throwing
      expect(find.byType(MaterialApp), findsOneWidget);
    });
  });

  group('Navigation smoke tests', () {
    testWidgets('VaultScreen shows module grid cards',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithProviders(const VaultScreen()));
      await tester.pumpAndSettle(_settleTimeout);

      // The Vault dashboard shows module cards for Observer, Shield, Deceptor,
      // Phantom Snare
      expect(find.textContaining('Observer'), findsWidgets);
      expect(find.textContaining('Shield'), findsWidgets);
    });
  });
}
