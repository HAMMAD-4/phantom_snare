import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/deceptor_service.dart';
import '../models/exfiltration_attempt.dart';
import '../utils/app_theme.dart';
import '../widgets/alert_feed.dart';
import '../widgets/section_header.dart';

/// The Deceptor Screen – displays data poisoning activity.
class DeceptorScreen extends StatelessWidget {
  const DeceptorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.psychology, color: AppTheme.deceptorColor, size: 20),
            const SizedBox(width: 8),
            const Text('THE DECEPTOR'),
          ],
        ),
        leading: const BackButton(),
      ),
      body: Consumer<DeceptorService>(
        builder: (context, deceptor, _) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildStatusBanner(deceptor),
              const SizedBox(height: 20),
              _buildStatsRow(deceptor),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'HOW IT WORKS',
                icon: Icons.info_outline,
                color: AppTheme.deceptorColor,
              ),
              const SizedBox(height: 12),
              _buildExplainerCard(),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'INTERCEPTED EXFILTRATION ATTEMPTS',
                icon: Icons.security_update_warning,
                color: AppTheme.deceptorColor,
                badge: deceptor.interceptedAttempts.length.toString(),
              ),
              const SizedBox(height: 12),
              if (deceptor.interceptedAttempts.isEmpty)
                _buildEmptyState('Monitoring for data exfiltration...')
              else
                ...deceptor.interceptedAttempts.take(15).map(
                      (a) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _buildAttemptCard(a),
                      ),
                    ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'ALERTS',
                icon: Icons.notification_important,
                color: AppTheme.dangerColor,
              ),
              const SizedBox(height: 12),
              AlertFeed(alerts: deceptor.alerts, maxItems: 10),
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatusBanner(DeceptorService deceptor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.deceptorColor.withAlpha(20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.deceptorColor.withAlpha(80)),
      ),
      child: Row(
        children: [
          Icon(
            deceptor.isActive ? Icons.psychology : Icons.psychology_outlined,
            color: AppTheme.deceptorColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  deceptor.isActive ? 'Deception Active' : 'Deceptor Inactive',
                  style: TextStyle(
                    color: AppTheme.deceptorColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Intercepted: ${deceptor.interceptedAttempts.length} attempts',
                  style:
                      const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Switch(
            value: deceptor.isActive,
            onChanged: (val) =>
                val ? deceptor.activate() : deceptor.deactivate(),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow(DeceptorService deceptor) {
    return Row(
      children: [
        _buildStatCard(
          'Attempts\nIntercepted',
          '${deceptor.interceptedAttempts.length}',
          Icons.security_update_warning,
          AppTheme.deceptorColor,
        ),
        const SizedBox(width: 12),
        _buildStatCard(
          'Data\nPoisoned',
          _formatBytes(deceptor.totalBytesPoison),
          Icons.data_array,
          AppTheme.warningColor,
        ),
        const SizedBox(width: 12),
        _buildStatCard(
          'Real Data\nProtected',
          _formatBytes(deceptor.totalDataSaved),
          Icons.lock,
          AppTheme.shieldColor,
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
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            Text(
              label,
              style: const TextStyle(color: Colors.white54, fontSize: 10),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExplainerCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ...[
              (Icons.bug_report, 'Zip Bomb', AppTheme.dangerColor,
                  'Expands small payloads into gigabytes of garbage data, '
                      'crashing the attacker\'s storage system.'),
              (Icons.text_fields, 'Garbage Strings', AppTheme.warningColor,
                  'Replaces real text data with randomized unicode garbage '
                      'that poisons NLP/AI models.'),
              (Icons.image_not_supported, 'Malformed Metadata',
                  AppTheme.observerColor,
                  'Corrupts EXIF/metadata fields to confuse forensic tools '
                      'and break automated analysis.'),
              (Icons.contact_page, 'Phantom Contacts', AppTheme.shieldColor,
                  'Substitutes real contacts with thousands of fake identities '
                      'to dilute any stolen database.'),
            ].map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(item.$1, color: item.$3, size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.$2,
                            style: TextStyle(
                              color: item.$3,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                          Text(
                            item.$4,
                            style: const TextStyle(
                              color: Colors.white54,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAttemptCard(ExfiltrationAttempt attempt) {
    final methodColor = _methodColor(attempt.deceptionMethod);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: methodColor.withAlpha(30),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: methodColor.withAlpha(80)),
                  ),
                  child: Text(
                    attempt.deceptionLabel,
                    style: TextStyle(
                      color: methodColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.check_circle,
                    color: AppTheme.accentColor, size: 14),
                const SizedBox(width: 4),
                const Text(
                  'NEUTRALIZED',
                  style: TextStyle(
                    color: AppTheme.accentColor,
                    fontSize: 10,
                    letterSpacing: 1,
                  ),
                ),
                const Spacer(),
                Text(
                  _timeAgo(attempt.timestamp),
                  style:
                      const TextStyle(color: Colors.white38, fontSize: 10),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${attempt.appName} → ${attempt.dataType}',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                _buildSizeChip(
                  'Original',
                  _formatBytes(attempt.originalDataSizeBytes),
                  AppTheme.dangerColor,
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 6),
                  child:
                      Icon(Icons.arrow_forward, size: 14, color: Colors.white38),
                ),
                _buildSizeChip(
                  'Poisoned',
                  _formatBytes(attempt.poisonedDataSizeBytes),
                  AppTheme.accentColor,
                ),
                const Spacer(),
                Text(
                  '×${attempt.expansionRatio.toStringAsFixed(0)}',
                  style: const TextStyle(
                    color: AppTheme.warningColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSizeChip(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: Colors.white38, fontSize: 10),
        ),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
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

  Color _methodColor(String method) {
    switch (method) {
      case 'zip_bomb':
        return AppTheme.dangerColor;
      case 'garbage_strings':
        return AppTheme.warningColor;
      case 'malformed_metadata':
        return AppTheme.observerColor;
      case 'phantom_contacts':
        return AppTheme.shieldColor;
      case 'fake_location':
        return AppTheme.phantomColor;
      default:
        return AppTheme.primaryColor;
    }
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String _timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }
}
