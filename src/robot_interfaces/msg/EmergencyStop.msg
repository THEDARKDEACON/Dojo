# Emergency stop message for coordinating emergency stops across all components

# Timestamp when emergency stop was triggered/cleared
builtin_interfaces/Time timestamp

# Whether emergency stop is active
bool active

# Human-readable reason for the emergency stop
string reason

# Component or system that triggered the emergency stop
string source

# Sequence number for tracking emergency stop events
uint32 sequence