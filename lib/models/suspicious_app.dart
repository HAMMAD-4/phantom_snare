/// Represents a suspicious app or process detected by the Observer.
class SuspiciousApp {
  final String packageName;
  final String appName;
  final List<String> suspiciousPermissions;
  final List<String> detectedBehaviors;
  final DateTime firstDetected;
  final int accessAttempts;
  bool isBlocked;

  SuspiciousApp({
    required this.packageName,
    required this.appName,
    required this.suspiciousPermissions,
    required this.detectedBehaviors,
    required this.firstDetected,
    this.accessAttempts = 1,
    this.isBlocked = false,
  });

  /// Returns a risk score from 0-100.
  int get riskScore {
    int score = 0;
    score += suspiciousPermissions.length * 15;
    score += detectedBehaviors.length * 20;
    score += (accessAttempts > 10) ? 20 : accessAttempts * 2;
    return score.clamp(0, 100);
  }

  String get riskLabel {
    final s = riskScore;
    if (s >= 80) return 'CRITICAL';
    if (s >= 60) return 'HIGH';
    if (s >= 40) return 'MEDIUM';
    if (s >= 20) return 'LOW';
    return 'INFO';
  }
}
