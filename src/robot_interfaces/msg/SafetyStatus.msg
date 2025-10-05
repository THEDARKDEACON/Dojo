# Safety status message for the robot safety system

# Timestamp of this status message
builtin_interfaces/Time timestamp

# Emergency stop state
bool emergency_stop_active

# Overall safety level: "normal", "warning", "critical", "emergency"
string overall_safety_level

# Lists of active safety conditions by severity
string[] warning_conditions
string[] critical_conditions
string[] emergency_conditions

# Safety limits currently in effect
float32 max_linear_velocity
float32 max_angular_velocity
float32 obstacle_stop_distance
float32 obstacle_slow_distance