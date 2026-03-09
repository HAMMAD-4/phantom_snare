import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/observer_service.dart';
import '../services/shield_service.dart';
import '../services/deceptor_service.dart';
import '../services/phantom_snare_service.dart';
import '../services/vault_service.dart';
import '../utils/app_theme.dart';
import '../widgets/module_card.dart';
import '../widgets/alert_feed.dart';
import '../widgets/stats_row.dart';
import 'observer_screen.dart';
import 'shield_screen.dart';
import 'deceptor_screen.dart';
import 'phantom_snare_screen.dart';

/// The Vault – Main Dashboard / Command Center.
///
/// Provides real-time alerts, module status overviews, stats, and quick
/// navigation to each specialized module screen.
class VaultScreen extends StatefulWidget {
  const VaultScreen({super.key});

  @override
  State<VaultScreen> createState() => _VaultScreenState();
}

class _VaultScreenState extends State<VaultScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    // Auto-activate all modules on launch
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _activateAllModules();
    });
  }

  void _activateAllModules() {
    context.read<ObserverService>().activate();
    context.read<ShieldService>().activate();
    context.read<DeceptorService>().activate();
    context.read<PhantomSnareService>().activate();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedBuilder(
              animation: _pulseController,
              builder: (_, __) => Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.accentColor.withAlpha(
                    ((_pulseController.value * 200 + 55).round()),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            const Text('SENTINEL PRIVACY'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.description_outlined),
            tooltip: 'Forensic Report',
            onPressed: _showForensicReport,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Consumer4<ObserverService, ShieldService, DeceptorService,
          PhantomSnareService>(
        builder: (
          context,
          observer,
          shield,
          deceptor,
          phantom,
          _,
        ) {
          return RefreshIndicator(
            color: AppTheme.primaryColor,
            backgroundColor: AppTheme.cardColor,
            onRefresh: () async {
              // Just a visual refresh – real data updates via timers
              await Future.delayed(const Duration(milliseconds: 500));
            },
            child: CustomScrollView(
              slivers: [
                SliverPadding(
                  padding: const EdgeInsets.all(16),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate([
                      _buildSystemStatusHeader(
                          observer, shield, deceptor, phantom),
                      const SizedBox(height: 16),
                      _buildStatsRow(observer, shield, deceptor, phantom),
                      const SizedBox(height: 20),
                      _buildSectionTitle('MODULES'),
                      const SizedBox(height: 12),
                      _buildModuleGrid(observer, shield, deceptor, phantom),
                      const SizedBox(height: 20),
                      _buildSectionTitle('LIVE ALERT FEED'),
                      const SizedBox(height: 12),
                      AlertFeed(
                        alerts: [
                          ...observer.alerts,
                          ...shield.alerts,
                          ...deceptor.alerts,
                          ...phantom.alerts,
                        ]..sort((a, b) => b.timestamp.compareTo(a.timestamp)),
                        maxItems: 20,
                      ),
                      const SizedBox(height: 80),
                    ]),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSystemStatusHeader(
    ObserverService observer,
    ShieldService shield,
    DeceptorService deceptor,
    PhantomSnareService phantom,
  ) {
    final allActive =
        observer.isActive && shield.isActive && deceptor.isActive && phantom.isActive;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: allActive ? AppTheme.accentColor : AppTheme.warningColor,
          width: 1.5,
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppTheme.cardColor,
            allActive
                ? AppTheme.accentColor.withAlpha(20)
                : AppTheme.warningColor.withAlpha(20),
          ],
        ),
      ),
      child: Row(
        children: [
          AnimatedBuilder(
            animation: _pulseController,
            builder: (_, __) => Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: (allActive ? AppTheme.accentColor : AppTheme.warningColor)
                    .withAlpha(
                  ((_pulseController.value * 80 + 40).round()),
                ),
                border: Border.all(
                  color:
                      allActive ? AppTheme.accentColor : AppTheme.warningColor,
                  width: 2,
                ),
              ),
              child: Icon(
                allActive ? Icons.security : Icons.warning_amber_rounded,
                color:
                    allActive ? AppTheme.accentColor : AppTheme.warningColor,
                size: 24,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  allActive ? 'SYSTEM ARMED' : 'PARTIAL DEFENSE',
                  style: TextStyle(
                    color: allActive ? AppTheme.accentColor : AppTheme.warningColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  allActive
                      ? 'All 4 modules are active and monitoring'
                      : 'Some modules are inactive – tap to enable',
                  style: const TextStyle(
                    color: Colors.white60,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow(
    ObserverService observer,
    ShieldService shield,
    DeceptorService deceptor,
    PhantomSnareService phantom,
  ) {
    return StatsRow(
      stats: [
        StatItem(
          label: 'THREATS\nDETECTED',
          value: '${observer.status.threatsBlocked + shield.status.threatsBlocked}',
          color: AppTheme.dangerColor,
        ),
        StatItem(
          label: 'C2 SERVERS\nBLOCKED',
          value: '${shield.totalBlockedConnections}',
          color: AppTheme.shieldColor,
        ),
        StatItem(
          label: 'DATA\nPOISONED',
          value: _formatBytes(deceptor.totalBytesPoison),
          color: AppTheme.deceptorColor,
        ),
        StatItem(
          label: 'SNARE\nEVENTS',
          value: '${phantom.status.eventsHandled}',
          color: AppTheme.phantomColor,
        ),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 16,
          decoration: BoxDecoration(
            color: AppTheme.primaryColor,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            color: AppTheme.primaryColor,
            fontSize: 12,
            fontWeight: FontWeight.bold,
            letterSpacing: 2,
          ),
        ),
      ],
    );
  }

  Widget _buildModuleGrid(
    ObserverService observer,
    ShieldService shield,
    DeceptorService deceptor,
    PhantomSnareService phantom,
  ) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: ModuleCard(
                title: 'Observer',
                subtitle: 'Forensic Collection',
                icon: Icons.radar,
                color: AppTheme.observerColor,
                isActive: observer.isActive,
                eventsCount: observer.status.eventsHandled,
                onTap: () => _navigateTo(const ObserverScreen()),
                onToggle: (val) => val
                    ? observer.activate()
                    : observer.deactivate(),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModuleCard(
                title: 'Shield',
                subtitle: 'C2 Firewall',
                icon: Icons.shield,
                color: AppTheme.shieldColor,
                isActive: shield.isActive,
                eventsCount: shield.status.threatsBlocked,
                onTap: () => _navigateTo(const ShieldScreen()),
                onToggle: (val) =>
                    val ? shield.activate() : shield.deactivate(),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ModuleCard(
                title: 'Deceptor',
                subtitle: 'Data Poisoning',
                icon: Icons.psychology,
                color: AppTheme.deceptorColor,
                isActive: deceptor.isActive,
                eventsCount: deceptor.interceptedAttempts.length,
                onTap: () => _navigateTo(const DeceptorScreen()),
                onToggle: (val) => val
                    ? deceptor.activate()
                    : deceptor.deactivate(),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModuleCard(
                title: 'Phantom Snare',
                subtitle: 'GPS/RF Spoofing',
                icon: Icons.gps_off,
                color: AppTheme.phantomColor,
                isActive: phantom.isActive,
                eventsCount: phantom.status.eventsHandled,
                onTap: () => _navigateTo(const PhantomSnareScreen()),
                onToggle: (val) => val
                    ? phantom.activate()
                    : phantom.deactivate(),
              ),
            ),
          ],
        ),
      ],
    );
  }

  void _navigateTo(Widget screen) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => screen),
    );
  }

  void _showForensicReport() {
    final report = context.read<VaultService>().generateForensicReport();
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: AppTheme.cardColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.description, color: AppTheme.primaryColor),
                  const SizedBox(width: 8),
                  const Text(
                    'FORENSIC REPORT',
                    style: TextStyle(
                      color: AppTheme.primaryColor,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 2,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white54),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const Divider(color: AppTheme.borderColor),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(ctx).size.height * 0.5,
                ),
                child: SingleChildScrollView(
                  child: Text(
                    report.isEmpty
                        ? 'No events recorded yet. Activate modules to begin.'
                        : report,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
