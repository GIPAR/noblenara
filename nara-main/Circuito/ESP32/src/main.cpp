#include <Arduino.h>
#include <micro_ros_platformio.h>
#include "noblenara_config.h"

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <Adafruit_MPU6050.h>       //IMU
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <ESP32Encoder.h>           //ENCODER
#include <driver/mcpwm.h>           //Ponte H
#include "soc/mcpwm_periph.h" 

#include <sensor_msgs/msg/imu.h>    //Messages
#include <nav_msgs/msg/odometry.h>  
#include <geometry_msgs/msg/twist.h>
#include <std_msgs/msg/string.h>    //topic for manual debugging

#include <QuickPID.h>

// MicroROS
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rclc_executor_t executor;

//Publishers | Subscribers | Messages - MicroROS
//rcl_publisher_t imu_pub;
//sensor_msgs__msg__Imu imu_msg;
//rcl_timer_t timer_imu;

rcl_publisher_t chat_pub;
std_msgs__msg__String chat_msg;

rcl_subscription_t cmd_vel_sub;
geometry_msgs__msg__Twist cmd_vel_msg;
rcl_publisher_t encoder_pub;
nav_msgs__msg__Odometry encoder_msg;
rcl_timer_t timer_watchdog;

// MPU6050
//Adafruit_MPU6050 mpu;

// ENCODER
ESP32Encoder encoderLeft;
ESP32Encoder encoderRight;

//Variáveis
int64_t CountLeft = 0;            //Variáveis para armazenar contagens atuais
int64_t CountRight = 0;
double newLeft = 0;               //Variáveis para armazenar distancia
double newRight = 0;
double newCenter = 0;

double posX = 0.0;                // Variáveis para odometria
double posY = 0.0;
double theta = 0.0;

double linearVel = 0.0;           // Variáveis de velocidade
double angularVel = 0.0;
double targetlinearVel = 0.0;
double targetangularVel = 0.0;
double targetleftVel = 0.0;
double targetrightVel = 0.0;

float timestamp = 0;              // Timestamp para cálculo de velocidade
float timehelper = 0;
float dt = 0;
unsigned long watchdog_cmdvel = 0;

// PID variables
float input_left, output_left, setpoint_left;
float input_right, output_right, setpoint_right;

// Create PID objects with TIMER mode
QuickPID pidLeft(&input_left, &output_left, &setpoint_left, 
                 K_P, K_I, K_D, 
                 QuickPID::Action::direct);
                 
QuickPID pidRight(&input_right, &output_right, &setpoint_right,
                 K_P, K_I, K_D,
                 QuickPID::Action::direct);

void callback_watchdog();
void callback_encoder();

void chat_publisher(const char* message, int number){
  char chat_buf[64];
  snprintf(chat_buf, sizeof(chat_buf), message, number);
  chat_msg.data.data = chat_buf;
  chat_msg.data.size = strlen(chat_buf);
  chat_msg.data.capacity = sizeof(chat_buf);
  rcl_publish(&chat_pub, &chat_msg, NULL);
}

//Funções Callbacks que são chamados pelo executor do ROS no loop
void callback_cmd_vel(const void * msgin){
  //Possivelmente no futuro: Combinar (PID + Velocity Profiling):
  watchdog_cmdvel = millis();

  geometry_msgs__msg__Twist * msg = (geometry_msgs__msg__Twist *) msgin;
  targetlinearVel = msg->linear.x;
  targetangularVel = msg->angular.z;

  targetleftVel = targetlinearVel - (targetangularVel * WHEEL_LR_DISTANCE / 2.0);
  targetrightVel = targetlinearVel + (targetangularVel * WHEEL_LR_DISTANCE / 2.0);
}

void callback_motorcontrol(){
  input_left = newLeft / dt;
  input_right = newRight / dt;
  
  setpoint_left = targetleftVel;
  setpoint_right = targetrightVel;

  if(pidRight.Compute()){
    if(output_right >=0){
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, output_right);
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    }
    else{
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(output_right));
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }
  }
  if(pidLeft.Compute()){
    if(output_left >=0){
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, output_left);
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    }
    else{
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(output_left));
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }
  }
}

void callback_encoder(){
  CountLeft = encoderLeft.getCount();
  CountRight = encoderRight.getCount();

  newLeft = CountLeft * METERS_PER_COUNT;                      //Atualizando as variáveis de armazenamento
  newRight = CountRight * METERS_PER_COUNT;
  newCenter = (newLeft + newRight) / 2.0;        

  timestamp = millis();
  dt = (timestamp - timehelper) / 1000.0;
  linearVel = newCenter / dt;
  angularVel = ((newRight - newLeft) / WHEEL_LR_DISTANCE) / dt;

  theta = theta + ((newRight - newLeft) / WHEEL_LR_DISTANCE);   //Atualizando as variáveis de posição absoluta
  posX = posX + (newCenter * cos(theta));
  posY = posY + (newCenter * sin(theta));

  // Preencher mensagem Odometry
  encoder_msg.header.stamp.sec = rmw_uros_epoch_millis() / 1000;
  encoder_msg.header.stamp.nanosec = rmw_uros_epoch_nanos();
  
  encoder_msg.pose.pose.position.x = posX;
  encoder_msg.pose.pose.position.y = posY;
  encoder_msg.pose.pose.position.z = 0.0;
  
  // Quaternion simplificado (só rotação em Z)
  encoder_msg.pose.pose.orientation.x = 0.0;
  encoder_msg.pose.pose.orientation.y = 0.0;
  encoder_msg.pose.pose.orientation.z = sin(theta / 2.0);
  encoder_msg.pose.pose.orientation.w = cos(theta / 2.0);
  
  encoder_msg.twist.twist.linear.x = linearVel;
  encoder_msg.twist.twist.linear.y = 0.0;
  encoder_msg.twist.twist.linear.z = 0.0;
  
  encoder_msg.twist.twist.angular.x = 0.0;
  encoder_msg.twist.twist.angular.y = 0.0;
  encoder_msg.twist.twist.angular.z = angularVel;
}

void callback_watchdog(rcl_timer_t * timer, int64_t last_call_time){
  if (timer == NULL) return;

  if (millis() - watchdog_cmdvel >= CMD_TIMEOUT_MS){
    targetleftVel = 0.0;
    targetrightVel = 0.0;
    pidLeft.Reset();
    pidRight.Reset();
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
  };

  callback_encoder();
  timehelper = millis();
  encoderLeft.clearCount();
  encoderRight.clearCount();
  callback_motorcontrol();
  rcl_ret_t ret = rcl_publish(&encoder_pub, &encoder_msg, NULL);
  if (ret != RCL_RET_OK) {
    chat_publisher("Falha na publicação da odometria!; Código ", ret);

    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
  }
}

void setup() {
  Serial.begin(115200);
  
  // CONFIGURAÇÕES
  set_microros_serial_transports(Serial);                   //CONFIG microROS
  delay(500);

  //ENCODER
  ESP32Encoder::useInternalWeakPullResistors = UP;        // ou DOWN/NONE, dependendo do seu hardware
  encoderLeft.attachFullQuad(ENCODER_LEFT_A, ENCODER_LEFT_B);
  encoderRight.attachFullQuad(ENCODER_RIGHT_A, ENCODER_RIGHT_B);

  encoderLeft.clearCount();                                 // Zerar contadores
  encoderRight.clearCount();

  pinMode(MOTOR_EN, OUTPUT);
  digitalWrite(MOTOR_EN, HIGH);   // Enable both BTS7960 drivers

  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, MOTOR_LEFT_RPWM);
  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, MOTOR_LEFT_LPWM);
  mcpwm_gpio_init(MCPWM_UNIT_1, MCPWM0A, MOTOR_RIGHT_RPWM);
  mcpwm_gpio_init(MCPWM_UNIT_1, MCPWM0B, MOTOR_RIGHT_LPWM);

  // MCPWM configuration structure
  mcpwm_config_t pwm_config;
  pwm_config.frequency = 20000;           // 20kHz - good for BTS7960
  pwm_config.cmpr_a = 0;                  // Start at 0% duty cycle
  pwm_config.cmpr_b = 0;                  // Start at 0% duty cycle
  pwm_config.counter_mode = MCPWM_UP_COUNTER;
  pwm_config.duty_mode = MCPWM_DUTY_MODE_0;  // Active high

  mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
  mcpwm_init(MCPWM_UNIT_1, MCPWM_TIMER_0, &pwm_config);

  // PID COnfiguration -> Set to TIMER mode (called by external timer)
  pidLeft.SetMode(QuickPID::Control::timer);
  pidLeft.SetOutputLimits(-100.0, 100.0);  // ← Changed to percentage!
  pidLeft.SetSampleTimeUs(20000); // 20ms = 50Hz
  
  pidRight.SetMode(QuickPID::Control::timer);
  pidRight.SetOutputLimits(-100.0, 100.0);  // ← Changed to percentage!
  pidRight.SetSampleTimeUs(20000);

  //Variáveis de tempo
  timehelper = millis();                                    // Inicializar timestamp      ***
  watchdog_cmdvel = millis();                               //Inicializar o timing do watchdog pra não dar bug

  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_imu", "", &support);

  // Criar publisher Encoder
  rclc_publisher_init_default(
    &encoder_pub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry),
    ODOM_TOPIC);

  rclc_subscription_init_default(
    &cmd_vel_sub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    CMD_VEL_TOPIC);

  // Configurar timer e executor || RCL_MS_TO_NS(20) para mudar a frequencia -- 20 = 50Hz
  rclc_timer_init_default2(&timer_watchdog, &support, RCL_MS_TO_NS(WATCHDOG_PUBLISH_RATE), callback_watchdog, true);
  rclc_executor_init(&executor, &support.context, 2, &allocator);
  rclc_executor_add_timer(&executor, &timer_watchdog);
  rclc_executor_add_subscription(&executor, &cmd_vel_sub, &cmd_vel_msg, &callback_cmd_vel, ON_NEW_DATA);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
}