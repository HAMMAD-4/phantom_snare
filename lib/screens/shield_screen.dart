import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/shield_service.dart';
import '../models/network_entry.dart';
import '../utils/app_theme.dart';
import '../widgets/alert_feed.dart';
import '../widgets/section_header.dart';

/// The Shield Screen – displays the firewall and C2 server blocklist.
class ShieldScreen extends StatelessWidget {
  const ShieldScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.shield, color: AppTheme.shieldColor, size: 20),
            const SizedBox(width: 8),
            const Text('THE SHIELD'),
          ],
        ),
        leading: const BackButton(),
      ),
      body: Consumer<ShieldService>(
        builder: (context, shield, _) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildStatusBanner(shield),
              const SizedBox(height: 20),
              _buildStatsRow(shield),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'BLOCKED C2 SERVERS',
                icon: Icons.block,
                color: AppTheme.shieldColor,
                badge: shield.blockedIPs.length.toString(),
              ),
              const SizedBox(height: 12),
              _buildBlocklist(shield),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'RECENT BLOCKED CONNECTIONS',
                icon: Icons.link_off,
                color: AppTheme.dangerColor,
                badge: shield.blockedConnections.length.toString(),
              ),
              const SizedBox(height: 12),
              ...shield.blockedConnections.take(15).map(
                    (entry) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: _buildBlockedConnectionRow(entry),
                    ),
                  ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'ALERTS',
                icon: Icons.notification_important,
                color: AppTheme.dangerColor,
              ),
              const SizedBox(height: 12),
              AlertFeed(alerts: shield.alerts, maxItems: 10),
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatusBanner(ShieldService shield) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.shieldColor.withAlpha(20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.shieldColor.withAlpha(80)),
      ),
      child: Row(
        children: [
          Icon(
            shield.isActive ? Icons.shield : Icons.shield_outlined,
            color: AppTheme.shieldColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  shield.isActive ? 'Firewall Active' : 'Firewall Inactive',
                  style: TextStyle(
                    color: AppTheme.shieldColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Blocked: ${shield.totalBlockedConnections} connections',
                  style: const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Switch(
            value: shield.isActive,
            onChanged: (val) =>
                val ? shield.activate() : shield.deactivate(),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow(ShieldService shield) {
    return Row(
      children: [
        _buildStatCard(
          'Total Blocked',
          '${shield.totalBlockedConnections}',
          Icons.block,
          AppTheme.dangerColor,
        ),
        const SizedBox(width: 12),
        _buildStatCard(
          'Blocklist IPs',
          '${shield.blockedIPs.length}',
          Icons.list_alt,
          AppTheme.shieldColor,
        ),
        const SizedBox(width: 12),
        _buildStatCard(
          'Threats/Min',
          shield.isActive ? '~${(60 / 3).round()}' : '0',
          Icons.speed,
          AppTheme.warningColor,
        ),
      ],
    );
  }

  Widget _buildStatCard(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withAlpha(15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withAlpha(50)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white54,
                fontSize: 10,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBlocklist(ShieldService shield) {
    return Card(
      child: Column(
        children: shield.blockedIPs.map((ip) {
          return ListTile(
            dense: true,
            leading: const Icon(
              Icons.block,
              color: AppTheme.dangerColor,
              size: 16,
            ),
            title: Text(
              ip,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 13,
                fontFamily: 'monospace',
              ),
            ),
            subtitle: const Text(
              'C2 Server — Blocked',
              style: TextStyle(color: Colors.white38, fontSize: 11),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.remove_circle_outline,
                  color: Colors.white38, size: 18),
              tooltip: 'Remove from blocklist',
              onPressed: () => shield.removeFromBlocklist(ip),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildBlockedConnectionRow(NetworkEntry entry) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.dangerColor.withAlpha(15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.dangerColor.withAlpha(50)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.link_off,
            size: 14,
            color: AppTheme.dangerColor,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${entry.sourceIp} ✗→ ${entry.destinationIp}:${entry.port}',
              style: const TextStyle(color: Colors.white70, fontSize: 11),
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
}
