/***************************************************************
   Motor driver implementation for L298N motor driver
   Modified for Dojo Robot Project
 ***************************************************************/

#ifdef USE_BASE

void initMotorController() {
  // Set motor enable pins to HIGH to enable the motors
  digitalWrite(RIGHT_MOTOR_ENABLE, HIGH);
  digitalWrite(LEFT_MOTOR_ENABLE, HIGH);
}

void setMotorSpeed(int i, int spd) {
  unsigned char reverse = 0;

  if (spd < 0) {
    spd = -spd;
    reverse = 1;
  }
  if (spd > 255)
    spd = 255;
  
  if (i == LEFT) { 
    if (reverse == 0) { 
      analogWrite(LEFT_MOTOR_FORWARD, spd); 
      analogWrite(LEFT_MOTOR_BACKWARD, 0); 
    }
    else if (reverse == 1) { 
      analogWrite(LEFT_MOTOR_BACKWARD, spd); 
      analogWrite(LEFT_MOTOR_FORWARD, 0); 
    }
  }
  else { // RIGHT motor
    if (reverse == 0) { 
      analogWrite(RIGHT_MOTOR_FORWARD, spd); 
      analogWrite(RIGHT_MOTOR_BACKWARD, 0); 
    }
    else if (reverse == 1) { 
      analogWrite(RIGHT_MOTOR_BACKWARD, spd); 
      analogWrite(RIGHT_MOTOR_FORWARD, 0); 
    }
  }
}

void setMotorSpeeds(int leftSpeed, int rightSpeed) {
  setMotorSpeed(LEFT, leftSpeed);
  setMotorSpeed(RIGHT, rightSpeed);
}

#endif