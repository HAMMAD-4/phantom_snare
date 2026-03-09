/// Operational status of a single SentinelPrivacy module.
class ModuleStatus {
  final String id;
  final String name;
  final String description;
  bool isActive;
  int eventsHandled;
  int threatsBlocked;
  DateTime? lastEventTime;

  ModuleStatus({
    required this.id,
    required this.name,
    required this.description,
    this.isActive = false,
    this.eventsHandled = 0,
    this.threatsBlocked = 0,
    this.lastEventTime,
  });

  void recordEvent({bool isThreat = false}) {
    eventsHandled++;
    if (isThreat) threatsBlocked++;
    lastEventTime = DateTime.now();
  }
}
