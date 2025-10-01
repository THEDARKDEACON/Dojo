/* *************************************************************
   Encoder driver function definitions - by James Nugen
   Modified for Dojo Robot with direct encoder connections
   ************************************************************ */
   
#ifdef ARDUINO_ENC_COUNTER
  // Encoder pin definitions for Arduino Mega
  // These should be interrupt-capable pins
  #define LEFT_ENC_PIN_A  2   // pin 2 (INT0)
  #define LEFT_ENC_PIN_B  3   // pin 3 (INT1)
  #define RIGHT_ENC_PIN_A 18  // pin 18 (INT5)
  #define RIGHT_ENC_PIN_B 19  // pin 19 (INT4)
#endif
   
long readEncoder(int i);
void resetEncoder(int i);
void resetEncoders();