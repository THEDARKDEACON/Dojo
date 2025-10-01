# ROSArduinoBridge for Dojo Robot

This is a complete implementation of the ROSArduinoBridge Arduino sketch, adapted for the Dojo robot project. It provides a simple serial communication protocol between ROS 2 and Arduino for controlling a differential drive robot.

## Hardware Requirements

- **Arduino Mega 2560**
- **L298N Motor Driver**
- **Quadrature Encoders** (connected directly to Arduino interrupt pins)

## Pin Configuration

### Motor Driver (L298N)
- **Left Motor:**
  - ENA (Enable): Pin 6 (PWM)
  - IN1 (Forward): Pin 7
  - IN2 (Backward): Pin 8

- **Right Motor:**
  - ENB (Enable): Pin 11 (PWM)
  - IN3 (Forward): Pin 9
  - IN4 (Backward): Pin 10

### Encoders
- **Left Encoder:**
  - Channel A: Pin 2 (INT0)
  - Channel B: Pin 3 (INT1)

- **Right Encoder:**
  - Channel A: Pin 18 (INT5)
  - Channel B: Pin 19 (INT4)

## Communication Protocol

The Arduino listens for single-letter commands over serial at **57600 baud**:

### Motor Control Commands
- `m <left_ticks> <right_ticks>\r` - Set target speeds in ticks per frame
- `o <left_pwm> <right_pwm>\r` - Set raw PWM values (bypasses PID)

### Encoder Commands
- `e\r` - Read encoder values (returns: "left_ticks right_ticks")
- `r\r` - Reset encoder counts to zero

### PID Control
- `u <kp>:<kd>:<ki>:<ko>\r` - Update PID parameters

### Utility Commands
- `b\r` - Get baud rate
- `a <pin>\r` - Analog read
- `d <pin>\r` - Digital read
- `w <pin> <value>\r` - Digital write
- `x <pin> <value>\r` - Analog write
- `c <pin> <mode>\r` - Set pin mode
- `p <pin>\r` - Ping sensor

## Features

- **PID Control**: Closed-loop speed control at 30Hz
- **Auto-stop**: Motors stop if no command received for 2 seconds
- **Encoder Feedback**: Real-time encoder position tracking
- **Safety**: Built-in command validation and motor limits

## Usage with ROS 2

This sketch is compatible with the `arduino_comms.cpp` interface used in the robosync project. The ROS 2 node sends commands like:

```cpp
// Read encoders
sendMsg("e\r");  // Returns: "1234 5678"

// Set motor speeds (ticks per frame)
sendMsg("m 10 -5\r");  // Left: 10, Right: -5

// Update PID gains
sendMsg("u 20:12:0:50\r");  // Kp:Kd:Ki:Ko
```

## Installation

1. Open `ROSArduinoBridge.ino` in Arduino IDE
2. Select **Arduino Mega 2560** as the board
3. Upload to your Arduino
4. Connect your L298N motor driver and encoders according to the pin configuration
5. Test communication at 57600 baud

## PID Tuning

Default PID parameters:
- Kp = 20
- Kd = 12  
- Ki = 0
- Ko = 50

Adjust these values using the `u` command or by modifying `diff_controller.h`.

## Troubleshooting

- **No response**: Check baud rate (57600) and serial connection
- **Motors not moving**: Verify L298N wiring and power supply
- **Erratic encoder readings**: Check encoder wiring and pull-up resistors
- **PID oscillation**: Reduce Kp and Kd values

## Files Structure

- `ROSArduinoBridge.ino` - Main sketch
- `commands.h` - Command definitions
- `motor_driver.h/.ino` - L298N motor control
- `encoder_driver.h/.ino` - Encoder reading
- `diff_controller.h` - PID control implementation
- `sensors.h` - Sensor utilities (ping, etc.)

This implementation provides a robust foundation for ROS 2 robot control with Arduino!