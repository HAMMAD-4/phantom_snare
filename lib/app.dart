import 'package:flutter/material.dart';

import 'screens/vault_screen.dart';
import 'utils/app_theme.dart';

class SentinelPrivacyApp extends StatelessWidget {
  const SentinelPrivacyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SentinelPrivacy',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const VaultScreen(),
    );
  }
}
