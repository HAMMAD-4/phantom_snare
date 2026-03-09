/// Represents a known or detected C2 (Command & Control) server entry.
class C2Server {
  final String id;
  final String ipAddress;
  final String domain;
  final String country;
  final String threatActor;
  final String malwareFamily;
  final DateTime firstSeen;
  final DateTime lastSeen;
  bool isBlocked;
  int connectionAttempts;

  C2Server({
    required this.id,
    required this.ipAddress,
    required this.domain,
    required this.country,
    required this.threatActor,
    required this.malwareFamily,
    required this.firstSeen,
    required this.lastSeen,
    this.isBlocked = true,
    this.connectionAttempts = 0,
  });
}

/// Network traffic entry captured by the Observer/Shield.
class NetworkEntry {
  final String id;
  final String sourceIp;
  final String destinationIp;
  final int port;
  final String protocol;
  final int bytesTransferred;
  final DateTime timestamp;
  final bool isMalicious;
  final String? threatType;

  const NetworkEntry({
    required this.id,
    required this.sourceIp,
    required this.destinationIp,
    required this.port,
    required this.protocol,
    required this.bytesTransferred,
    required this.timestamp,
    this.isMalicious = false,
    this.threatType,
  });
}
