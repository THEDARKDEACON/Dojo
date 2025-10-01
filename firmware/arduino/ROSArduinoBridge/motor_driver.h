/***************************************************************
   Motor driver function definitions - by James Nugen
   Modified for Dojo Robot with L298N motor driver
   *************************************************************/

#ifdef L298_MOTOR_DRIVER
  // L298N Motor Driver Pin Definitions for Arduino Mega
  #define RIGHT_MOTOR_ENABLE 11    // L298N ENB (PWM)
  #define RIGHT_MOTOR_FORWARD  9   // L298N IN3
  #define RIGHT_MOTOR_BACKWARD 10  // L298N IN4
  #define LEFT_MOTOR_ENABLE 6      // L298N ENA (PWM)
  #define LEFT_MOTOR_FORWARD   7   // L298N IN1
  #define LEFT_MOTOR_BACKWARD  8   // L298N IN2
#endif

void initMotorController();
void setMotorSpeed(int i, int spd);
void setMotorSpeeds(int leftSpeed, int rightSpeed);