import 'package:flutter/material.dart';

import '../models/security_alert.dart';
/// A scrollable feed of [SecurityAlert]s.
class AlertFeed extends StatelessWidget {
  final List<SecurityAlert> alerts;
  final int maxItems;

  const AlertFeed({
    super.key,
    required this.alerts,
    this.maxItems = 20,
  });

  @override
  Widget build(BuildContext context) {
    final displayed = alerts.take(maxItems).toList();

    if (displayed.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(
          child: Text(
            'No alerts yet',
            style: TextStyle(color: Colors.white38, fontSize: 13),
          ),
        ),
      );
    }

    return Column(
      children: displayed.map((alert) => _AlertItem(alert: alert)).toList(),
    );
  }
}

class _AlertItem extends StatelessWidget {
  final SecurityAlert alert;

  const _AlertItem({required this.alert});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: alert.severityColor.withAlpha(10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: alert.severityColor.withAlpha(40),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 2),
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
            decoration: BoxDecoration(
              color: alert.severityColor.withAlpha(30),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              alert.severityLabel,
              style: TextStyle(
                color: alert.severityColor,
                fontSize: 9,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      alert.sourceIcon,
                      size: 12,
                      color: Colors.white38,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      alert.sourceLabel,
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 10,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      _timeAgo(alert.timestamp),
                      style: const TextStyle(
                        color: Colors.white30,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  alert.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  alert.description,
                  style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 11,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }
}
