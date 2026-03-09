/// Represents a data exfiltration attempt intercepted by the Deceptor.
class ExfiltrationAttempt {
  final String id;
  final String appName;
  final String dataType;
  final int originalDataSizeBytes;
  final int poisonedDataSizeBytes;
  final String deceptionMethod;
  final DateTime timestamp;
  bool isNeutralized;

  ExfiltrationAttempt({
    required this.id,
    required this.appName,
    required this.dataType,
    required this.originalDataSizeBytes,
    required this.poisonedDataSizeBytes,
    required this.deceptionMethod,
    required this.timestamp,
    this.isNeutralized = true,
  });

  /// Ratio of poisoned data to original data (expansion factor).
  double get expansionRatio =>
      poisonedDataSizeBytes / (originalDataSizeBytes == 0 ? 1 : originalDataSizeBytes);

  String get deceptionLabel {
    switch (deceptionMethod) {
      case 'zip_bomb':
        return 'Zip Bomb';
      case 'garbage_strings':
        return 'Garbage Strings';
      case 'malformed_metadata':
        return 'Malformed Metadata';
      case 'phantom_contacts':
        return 'Phantom Contacts';
      case 'fake_location':
        return 'Fake Location';
      default:
        return deceptionMethod;
    }
  }
}
