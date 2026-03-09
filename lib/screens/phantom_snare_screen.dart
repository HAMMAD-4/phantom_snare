import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/phantom_snare_service.dart';
import '../models/spoofing_event.dart';
import '../utils/app_theme.dart';
import '../widgets/alert_feed.dart';
import '../widgets/section_header.dart';
import '../widgets/coordinate_display.dart';

/// The Phantom Snare Screen – GPS/RF spoofing control panel.
///
/// Shows the phantom vs. real coordinates and lets the user configure
/// which spoofing types are active.
class PhantomSnareScreen extends StatelessWidget {
  const PhantomSnareScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.gps_off, color: AppTheme.phantomColor, size: 20),
            const SizedBox(width: 8),
            const Text('PHANTOM SNARE'),
          ],
        ),
        leading: const BackButton(),
      ),
      body: Consumer<PhantomSnareService>(
        builder: (context, phantom, _) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildStatusBanner(phantom),
              const SizedBox(height: 20),
              _buildCoordinatePanel(phantom),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.phantomColor,
                  foregroundColor: Colors.black,
                ),
                icon: const Icon(Icons.shuffle),
                label: const Text('RANDOMIZE PHANTOM LOCATION'),
                onPressed: phantom.isActive
                    ? phantom.randomizePhantomLocation
                    : null,
              ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'SNARE CONFIGURATION',
                icon: Icons.tune,
                color: AppTheme.phantomColor,
              ),
              const SizedBox(height: 12),
              _buildSnareToggles(phantom),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'RECENT SPOOFING EVENTS',
                icon: Icons.history,
                color: AppTheme.phantomColor,
                badge: phantom.spoofingEvents.length.toString(),
              ),
              const SizedBox(height: 12),
              if (phantom.spoofingEvents.isEmpty)
                _buildEmptyState(
                  'No spoofing events yet.\nActivate the Snare to begin.',
                )
              else
                ...phantom.spoofingEvents.take(15).map(
                      (e) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _buildEventRow(e),
                      ),
                    ),
              const SizedBox(height: 20),
              SectionHeader(
                title: 'ALERTS',
                icon: Icons.notification_important,
                color: AppTheme.dangerColor,
              ),
              const SizedBox(height: 12),
              AlertFeed(alerts: phantom.alerts, maxItems: 10),
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatusBanner(PhantomSnareService phantom) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.phantomColor.withAlpha(20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.phantomColor.withAlpha(80)),
      ),
      child: Row(
        children: [
          Icon(
            phantom.isActive ? Icons.gps_off : Icons.gps_not_fixed,
            color: AppTheme.phantomColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  phantom.isActive ? 'Snare Active' : 'Snare Inactive',
                  style: TextStyle(
                    color: AppTheme.phantomColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Events handled: ${phantom.status.eventsHandled}',
                  style:
                      const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Switch(
            value: phantom.isActive,
            onChanged: (val) =>
                val ? phantom.activate() : phantom.deactivate(),
          ),
        ],
      ),
    );
  }

  Widget _buildCoordinatePanel(PhantomSnareService phantom) {
    return Row(
      children: [
        Expanded(
          child: CoordinateDisplay(
            label: 'REAL LOCATION',
            sublabel: '(Hidden from attackers)',
            lat: phantom.realLat,
            lon: phantom.realLon,
            color: AppTheme.dangerColor,
            icon: Icons.location_on,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: CoordinateDisplay(
            label: 'PHANTOM LOCATION',
            sublabel: '(Served to attackers)',
            lat: phantom.phantomLat,
            lon: phantom.phantomLon,
            color: AppTheme.phantomColor,
            icon: Icons.location_off,
          ),
        ),
      ],
    );
  }

  Widget _buildSnareToggles(PhantomSnareService phantom) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            _buildToggleTile(
              'GPS Spoofing',
              'Intercepts GPS location queries from malicious apps',
              Icons.gps_off,
              AppTheme.phantomColor,
              phantom.gpsSnareActive,
              phantom.setGpsSnare,
            ),
            const Divider(color: AppTheme.borderColor, height: 1),
            _buildToggleTile(
              'RF Scanner Noise',
              'Injects fake RF signal strength data to RF scanners',
              Icons.signal_cellular_alt,
              AppTheme.observerColor,
              phantom.rfSnareActive,
              phantom.setRfSnare,
            ),
            const Divider(color: AppTheme.borderColor, height: 1),
            _buildToggleTile(
              'Cell Tower Spoofing',
              'Reports fake cell tower triangulation data',
              Icons.cell_tower,
              AppTheme.shieldColor,
              phantom.cellTowerSnareActive,
              phantom.setCellTowerSnare,
            ),
            const Divider(color: AppTheme.borderColor, height: 1),
            _buildToggleTile(
              'Wi-Fi Probe Decoy',
              'Responds to Wi-Fi probe requests with phantom MAC/SSID',
              Icons.wifi_tethering_error,
              AppTheme.deceptorColor,
              phantom.wifiProbeSnareActive,
              phantom.setWifiProbeSnare,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleTile(
    String title,
    String subtitle,
    IconData icon,
    Color color,
    bool value,
    void Function(bool) onChanged,
  ) {
    return ListTile(
      leading: Icon(icon, color: color, size: 20),
      title: Text(
        title,
        style: const TextStyle(color: Colors.white, fontSize: 14),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(color: Colors.white54, fontSize: 11),
      ),
      trailing: Switch(value: value, onChanged: onChanged),
    );
  }

  Widget _buildEventRow(SpoofingEvent event) {
    final typeColor = _typeColor(event.type);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: typeColor.withAlpha(10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: typeColor.withAlpha(50)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(_typeIcon(event.type), color: typeColor, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      event.type.label,
                      style: TextStyle(
                        color: typeColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        event.triggerSource,
                        style: const TextStyle(
                          color: Colors.white54,
                          fontSize: 11,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      _timeAgo(event.timestamp),
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Phantom: (${event.phantomLatitude.toStringAsFixed(4)}, '
                  '${event.phantomLongitude.toStringAsFixed(4)})',
                  style: TextStyle(
                    color: typeColor.withAlpha(180),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
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

  Color _typeColor(SpoofingType type) {
    switch (type) {
      case SpoofingType.gps:
        return AppTheme.phantomColor;
      case SpoofingType.rfScanner:
        return AppTheme.observerColor;
      case SpoofingType.cellTower:
        return AppTheme.shieldColor;
      case SpoofingType.wifiProbe:
        return AppTheme.deceptorColor;
    }
  }

  IconData _typeIcon(SpoofingType type) {
    switch (type) {
      case SpoofingType.gps:
        return Icons.gps_off;
      case SpoofingType.rfScanner:
        return Icons.signal_cellular_alt;
      case SpoofingType.cellTower:
        return Icons.cell_tower;
      case SpoofingType.wifiProbe:
        return Icons.wifi_tethering_error;
    }
  }

  String _timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ago';
  }
}
