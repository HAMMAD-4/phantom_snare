import 'package:flutter/material.dart';

import '../utils/app_theme.dart';

/// Displays a pair of GPS coordinates with label styling.
class CoordinateDisplay extends StatelessWidget {
  final String label;
  final String sublabel;
  final double lat;
  final double lon;
  final Color color;
  final IconData icon;

  const CoordinateDisplay({
    super.key,
    required this.label,
    required this.sublabel,
    required this.lat,
    required this.lon,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withAlpha(15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            sublabel,
            style: const TextStyle(color: Colors.white38, fontSize: 10),
          ),
          const SizedBox(height: 10),
          _coordRow('LAT', lat, color),
          const SizedBox(height: 4),
          _coordRow('LON', lon, color),
        ],
      ),
    );
  }

  Widget _coordRow(String axis, double value, Color color) {
    return Row(
      children: [
        Text(
          '$axis  ',
          style: const TextStyle(
            color: Colors.white38,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          value.toStringAsFixed(6),
          style: TextStyle(
            color: color,
            fontSize: 13,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
