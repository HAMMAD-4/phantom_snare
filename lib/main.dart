// This is the main entry point for SentinelPrivacy (Phantom Snare).
// It initializes all module providers and launches the app.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'services/observer_service.dart';
import 'services/shield_service.dart';
import 'services/deceptor_service.dart';
import 'services/phantom_snare_service.dart';
import 'services/vault_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
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
}
