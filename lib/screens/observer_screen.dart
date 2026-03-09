import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/observer_service.dart';
import '../models/suspicious_app.dart';
import '../models/network_entry.dart';
import '../utils/app_theme.dart';
import '../widgets/alert_feed.dart';
import '../widgets/section_header.dart';

/// The Observer Screen – displays forensic collection data.
///
/// Shows detected suspicious apps, their risk scores, and the
/// live network traffic log.
class ObserverScreen extends StatelessWidget {
  const ObserverScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.radar, color: AppTheme.observerColor, size: 20),
            const SizedBox(width: 8),
            const Text('THE OBSERVER'),
          ],
        ),
        leading: const BackButton(),
      ),
      body: Consumer<ObserverService>(
        builder: (context, observer, _) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildStatusBanner(context, observer),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'SUSPICIOUS APPS',
                icon: Icons.apps,
                color: AppTheme.observerColor,
                badge: observer.detectedApps.length.toString(),
              ),
              const SizedBox(height: 12),
              if (observer.detectedApps.isEmpty)
                _buildEmptyState('Scanning for suspicious apps...')
              else
                ...observer.detectedApps.map(
                  (app) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _buildAppCard(context, app, observer),
                  ),
                ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'NETWORK TRAFFIC LOG',
                icon: Icons.network_check,
                color: AppTheme.observerColor,
                badge: observer.networkLog.length.toString(),
              ),
              const SizedBox(height: 12),
              if (observer.networkLog.isEmpty)
                _buildEmptyState('Waiting for network traffic...')
              else
                ...observer.networkLog.take(15).map(
                      (entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: _buildNetworkRow(entry),
                      ),
                    ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'ALERTS',
                icon: Icons.notification_important,
                color: AppTheme.dangerColor,
                badge: observer.alerts.length.toString(),
              ),
              const SizedBox(height: 12),
              AlertFeed(alerts: observer.alerts, maxItems: 10),
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatusBanner(BuildContext context, ObserverService observer) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.observerColor.withAlpha(20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.observerColor.withAlpha(80)),
      ),
      child: Row(
        children: [
          Icon(
            observer.isActive ? Icons.radar : Icons.radar_outlined,
            color: AppTheme.observerColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  observer.isActive
                      ? 'Monitoring Active'
                      : 'Observer Inactive',
                  style: TextStyle(
                    color: AppTheme.observerColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Events: ${observer.status.eventsHandled} | '
                  'Threats: ${observer.status.threatsBlocked}',
                  style: const TextStyle(
                    color: Colors.white60,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: observer.isActive,
            onChanged: (val) =>
                val ? observer.activate() : observer.deactivate(),
          ),
        ],
      ),
    );
  }

  Widget _buildAppCard(
    BuildContext context,
    SuspiciousApp app,
    ObserverService observer,
  ) {
    final riskColor = _riskColor(app.riskScore);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: riskColor.withAlpha(30),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: riskColor.withAlpha(80)),
                  ),
                  child: Text(
                    app.riskLabel,
                    style: TextStyle(
                      color: riskColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    app.appName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                if (app.isBlocked)
                  const Icon(
                    Icons.block,
                    color: AppTheme.dangerColor,
                    size: 16,
                  )
                else
                  TextButton(
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      minimumSize: Size.zero,
                    ),
                    onPressed: () => observer.blockApp(app.packageName),
                    child: const Text(
                      'BLOCK',
                      style: TextStyle(
                        color: AppTheme.dangerColor,
                        fontSize: 11,
                        letterSpacing: 1,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              app.packageName,
              style: const TextStyle(
                color: Colors.white38,
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 8),
            // Risk score bar
            Row(
              children: [
                const Text(
                  'Risk: ',
                  style: TextStyle(color: Colors.white54, fontSize: 12),
                ),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: app.riskScore / 100.0,
                      backgroundColor: AppTheme.borderColor,
                      valueColor: AlwaysStoppedAnimation<Color>(riskColor),
                      minHeight: 6,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '${app.riskScore}%',
                  style: TextStyle(
                    color: riskColor,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                ...app.suspiciousPermissions.map(
                  (p) => _buildChip(p, AppTheme.dangerColor),
                ),
                ...app.detectedBehaviors.map(
                  (b) => _buildChip(b, AppTheme.warningColor),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNetworkRow(NetworkEntry entry) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: entry.isMalicious
            ? AppTheme.dangerColor.withAlpha(15)
            : AppTheme.cardColor,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: entry.isMalicious
              ? AppTheme.dangerColor.withAlpha(60)
              : AppTheme.borderColor,
        ),
      ),
      child: Row(
        children: [
          Icon(
            entry.isMalicious ? Icons.warning_amber : Icons.check_circle_outline,
            size: 14,
            color: entry.isMalicious ? AppTheme.dangerColor : Colors.white30,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${entry.sourceIp} → ${entry.destinationIp}:${entry.port}',
              style: TextStyle(
                color: entry.isMalicious ? Colors.white : Colors.white54,
                fontSize: 11,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            entry.protocol,
            style: const TextStyle(color: Colors.white38, fontSize: 10),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(String message) {
    return Container(
      padding: const EdgeInsets.all(24),
      alignment: Alignment.center,
      child: Text(
        message,
        style: const TextStyle(color: Colors.white38, fontSize: 13),
        textAlign: TextAlign.center,
      ),
    );
  }

  Widget _buildChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 10),
      ),
    );
  }

  Color _riskColor(int score) {
    if (score >= 80) return AppTheme.dangerColor;
    if (score >= 60) return const Color(0xFFFF6B35);
    if (score >= 40) return AppTheme.warningColor;
    if (score >= 20) return AppTheme.observerColor;
    return Colors.white38;
  }
}
