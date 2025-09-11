#include <ros2arduino.h>
#include <Servo.h>   // ✅ Added for servo

// ================================
// Pin Definitions for L298N
// ================================

// Motor A (Left Motor)
#define IN1 8     // L298N IN1
#define IN2 9     // L298N IN2
#define ENA 5     // L298N ENA (PWM) - Left motor speed control

// Motor B (Right Motor)
#define IN3 10    // L298N IN3
#define IN4 11    // L298N IN4
#define ENB 6     // L298N ENB (PWM) - Right motor speed control

// Servo
#define SERVO_PIN 3
Servo myServo;

// Motor control parameters
#define MAX_PWM 255
#define MIN_PWM 30
#define DEADBAND 0.05
#define MAX_ACCEL 0.5
#define RAMP_RATE 0.5

// ROS2 Node
rcl_node_t node;
rclc_support_t support;
rcl_allocator_t allocator;

// Publishers
rcl_publisher_t imu_pub;
sensor_msgs__msg__Imu imu_msg;
rcl_publisher_t encoder_pub;
sensor_msgs__msg__JointState encoder_msg;

// Subscribers
rcl_subscription_t cmd_vel_sub;
geometry_msgs__msg__Twist cmd_vel_msg;

// ✅ New subscriber for servo
rcl_subscription_t servo_sub;
std_msgs__msg__String servo_msg;

// Timer for publishing sensor data
rcl_timer_t timer;
rclc_executor_t executor;

// Variables for sensors and motor control
float left_encoder = 0.0;
float right_encoder = 0.0;
float left_motor_output = 0.0;
float right_motor_output = 0.0;

// ✅ Global timeout tracker (fixed duplication bug)
unsigned long last_cmd_time = 0;

// Function prototypes
void setupROS2();
void timerCallback(rcl_timer_t *timer, int64_t last_call_time);
void cmdVelCallback(const void *msg_in);
void servoCallback(const void * msgin);   // ✅ new
void updateSensors();
void controlMotors(float linear, float angular);

void setup() {
  // Initialize Serial for debugging
  Serial.begin(115200);

  // Initialize motor control pins for L298N
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Initialize all pins to LOW (motors off)
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  // Initialize ROS2
  setupROS2();

  // Attach servo ✅
  myServo.attach(SERVO_PIN);

  // ✅ Default to closed position at startup
  myServo.write(0);    
  Serial.println("Servo initialized to closed");

  // Initial motor stop ✅ corrected
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  // Wait for ROS2 to be ready
  delay(1000);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
  updateSensors();
  delay(10);
}

void setupROS2() {
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);

  rclc_node_init_default(&node, "arduino_node", "", &support);

  // Publishers
  rclc_publisher_init_default(
    &imu_pub, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
    "imu/data");

  rclc_publisher_init_default(
    &encoder_pub, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
    "wheel_encoders");

  // Subscribers
  rclc_subscription_init_default(
    &cmd_vel_sub, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "cmd_vel");

  // ✅ Servo subscriber
  rclc_subscription_init_default(
    &servo_sub, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
    "servo_cmd");

  // Timer
  rclc_timer_init_default(&timer, &support, RCL_MS_TO_NS(100), timerCallback);

  // Executor
  rclc_executor_init(&executor, &support.context, 10, &allocator);
  rclc_executor_add_timer(&executor, &timer);

  rclc_executor_add_subscription(
    &executor, &cmd_vel_sub, &cmd_vel_msg, &cmdVelCallback, ON_NEW_DATA);

  // ✅ Add servo subscriber to executor
  rclc_executor_add_subscription(
    &executor, &servo_sub, &servo_msg, &servoCallback, ON_NEW_DATA);

  // Init messages
  sensor_msgs__msg__Imu__init(&imu_msg);
  sensor_msgs__msg__JointState__init(&encoder_msg);
  geometry_msgs__msg__Twist__init(&cmd_vel_msg);

  const char* joint_names[] = {"left_wheel_joint", "right_wheel_joint"};
  encoder_msg.name.size = 2;
  encoder_msg.name.data = (rosidl_runtime_c__String*)malloc(2 * sizeof(rosidl_runtime_c__String));
  for (int i = 0; i < 2; i++) {
    rosidl_runtime_c__String__assign(&encoder_msg.name.data[i], joint_names[i]);
  }
  encoder_msg.position.size = 2;
  encoder_msg.position.data = (double*)malloc(2 * sizeof(double));
  encoder_msg.velocity.size = 2;
  encoder_msg.velocity.data = (double*)malloc(2 * sizeof(double));
  encoder_msg.effort.size = 0;
  encoder_msg.effort.data = NULL;
}

void timerCallback(rcl_timer_t *timer, int64_t last_call_time) {
  (void)last_call_time;

  if (timer != NULL) {
    updateSensors();
    encoder_msg.header.stamp = micros_rolling_over_32();
    encoder_msg.position.data[0] = left_encoder;
    encoder_msg.position.data[1] = right_encoder;
    rcl_publish(&encoder_pub, &encoder_msg, NULL);
  }
}

void cmdVelCallback(const void *msg_in) {
  const geometry_msgs__msg__Twist *twist = (const geometry_msgs__msg__Twist *)msg_in;
  last_cmd_time = millis();   // ✅ update global

  float linear = constrain(twist->linear.x, -1.0, 1.0);
  float angular = constrain(twist->angular.z, -1.0, 1.0);

  float left = linear - angular;
  float right = linear + angular;
  float max_command = max(fabs(left), fabs(right));

  if (max_command > 1.0) {
    linear /= max_command;
    angular /= max_command;
  }

  controlMotors(linear, angular);
}

// ✅ Servo callback
void servoCallback(const void * msgin) {
  const std_msgs__msg__String * msg = (const std_msgs__msg__String *)msgin;
  String cmd = String(msg->data.data);
  cmd.trim();

  if (cmd == "open") {
    myServo.write(90);   // adjust angle for open
    Serial.println("Servo opened");
  } else if (cmd == "close") {
    myServo.write(0);    // adjust angle for closed
    Serial.println("Servo closed");
  }
}

void updateSensors() {
  static unsigned long last_encoder_update = 0;
  if (millis() - last_encoder_update > 50) {
    left_encoder += 0.1 * random(-10, 10);
    right_encoder += 0.1 * random(-10, 10);
    last_encoder_update = millis();
  }
}

void controlMotors(float linear, float angular) {
  if (millis() - last_cmd_time > 500) {   // ✅ uses global timeout
    left_motor_output = 0.0;
    right_motor_output = 0.0;
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    return;
  }

  float target_left = linear - angular;
  float target_right = linear + angular;

  if (fabs(target_left) < DEADBAND) target_left = 0.0;
  if (fabs(target_right) < DEADBAND) target_right = 0.0;

  float delta_left = target_left - left_motor_output;
  float delta_right = target_right - right_motor_output;

  delta_left = constrain(delta_left, -MAX_ACCEL, MAX_ACCEL);
  delta_right = constrain(delta_right, -MAX_ACCEL, MAX_ACCEL);

  left_motor_output += delta_left * RAMP_RATE;
  right_motor_output += delta_right * RAMP_RATE;

  int left_pwm = 0;
  int right_pwm = 0;

  if (fabs(left_motor_output) > 0) {
    left_pwm = (int)(fabs(left_motor_output) * (MAX_PWM - MIN_PWM) + MIN_PWM);
    left_pwm = constrain(left_pwm, 0, MAX_PWM);
  }

  if (fabs(right_motor_output) > 0) {
    right_pwm = (int)(fabs(right_motor_output) * (MAX_PWM - MIN_PWM) + MIN_PWM);
    right_pwm = constrain(right_pwm, 0, MAX_PWM);
  }

  if (left_motor_output > 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, left_pwm);
  } else if (left_motor_output < 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    analogWrite(ENA, left_pwm);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, 0);
  }

  if (right_motor_output > 0) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
    analogWrite(ENB, right_pwm);
  } else if (right_motor_output < 0) {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
    analogWrite(ENB, right_pwm);
  } else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    analogWrite(ENB, 0);
  }
}

