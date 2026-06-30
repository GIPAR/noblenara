#include <Arduino.h>
#include <micro_ros_platformio.h>
#include "noblenara_config.h"

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <ESP32Encoder.h>
#include <driver/mcpwm.h>
#include "soc/mcpwm_periph.h"

#include <sensor_msgs/msg/imu.h>
#include <nav_msgs/msg/odometry.h> 
#include <geometry_msgs/msg/twist.h>
#include <sensor_msgs/msg/battery_state.h>

#include <QuickPID.h>

// MicroROS
rclc_support_t support;
rcl_allocator_t allocator;
rcl_init_options_t init_options;
rcl_node_t node;
rclc_executor_t executor;
size_t ros_domain;

rcl_subscription_t cmd_vel_sub;
geometry_msgs__msg__Twist cmd_vel_msg;
rcl_publisher_t encoder_pub;
nav_msgs__msg__Odometry encoder_msg;
rcl_publisher_t imu_pub;
sensor_msgs__msg__Imu imu_msg;
rcl_timer_t timer_watchdog;

rcl_publisher_t battery_pub;
sensor_msgs__msg__BatteryState battery_msg;
rcl_timer_t timer_battery;

// MPU6050
Adafruit_MPU6050 mpu;

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

unsigned long timestamp = 0;              // Timestamp para cálculo de velocidade
unsigned long timehelper = 0;
float dt = 0;
unsigned long watchdog_cmdvel = 0;

// Variáveis e Objetos do PID com TIMER Mode
float input_left, output_left, setpoint_left;
float input_right, output_right, setpoint_right;

QuickPID pidLeft(&input_left, &output_left, &setpoint_left, 
                 K_P, K_I, K_D, 
                 QuickPID::Action::direct);
                 
QuickPID pidRight(&input_right, &output_right, &setpoint_right,
                 K_P, K_I, K_D,
                 QuickPID::Action::direct);

void callback_watchdog();
void callback_encoder();
void callback_imu();
void callback_battery();

//=============================================================================
//                        FUNÇÕES DE CONTROLE DE VELOCIDADE

void callback_cmd_vel(const void * msgin){
  watchdog_cmdvel = millis();

  geometry_msgs__msg__Twist * msg = (geometry_msgs__msg__Twist *) msgin;
  targetlinearVel = msg->linear.x;
  targetangularVel = msg->angular.z;

  targetleftVel = targetlinearVel - (targetangularVel * WHEEL_LR_DISTANCE / 2.0);
  targetrightVel = targetlinearVel + (targetangularVel * WHEEL_LR_DISTANCE / 2.0);
}

void callback_motorcontrol(){
    input_left  = newLeft  / dt;
    input_right = newRight / dt;
    setpoint_left  = targetleftVel;
    setpoint_right = targetrightVel;

    pidLeft.Compute();   
    pidRight.Compute();

    // ====================================================================
    // ZONA MORTA DINÂMICA INDEPENDENTE (Compensação de Assimetria)
    
    float DEADBAND_LEFT = 20.0;  
    float DEADBAND_RIGHT = 23.5; 

    float final_pwm_left = output_left;
    float final_pwm_right = output_right;

    // Compensação da Roda Esquerda
    if (setpoint_left > 0.05 && output_left < DEADBAND_LEFT && output_left > 0) {
        final_pwm_left = DEADBAND_LEFT;
    } else if (setpoint_left < -0.05 && output_left > -DEADBAND_LEFT && output_left < 0) {
        final_pwm_left = -DEADBAND_LEFT;
    }

    // Compensação da Roda Direita (O motor problemático)
    if (setpoint_right > 0.05 && output_right < DEADBAND_RIGHT && output_right > 0) {
        final_pwm_right = DEADBAND_RIGHT;
    } else if (setpoint_right < -0.05 && output_right > -DEADBAND_RIGHT && output_right < 0) {
        final_pwm_right = -DEADBAND_RIGHT;
    }

    // Desliga totalmente se o alvo for zero (Segurança)
    if (fabs(setpoint_left) < 0.01) final_pwm_left = 0.0;
    if (fabs(setpoint_right) < 0.01) final_pwm_right = 0.0;
    // ====================================================================

    // Motor direito (Usando o PWM compensado)
    if(final_pwm_right >= 0){
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, final_pwm_right);
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    } else {
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(final_pwm_right));
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }

    // Motor esquerdo (Usando o PWM compensado)
    if(final_pwm_left >= 0){
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, final_pwm_left);
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    } else {
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(final_pwm_left));
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }
}

//=============================================================================
//                        FUNÇÕES DE CÁLCULO

void callback_encoder(){
  CountLeft  = encoderLeft.getCount();
  CountRight = encoderRight.getCount();

  unsigned long now = millis();
  dt = (float)(now - timehelper) / 1000.0f;
  if (dt <= 0.0f) dt = 0.001f;  // guarda contra divisão por zero
  
  timehelper = now; // ATUALIZA O TEMPO AQUI, DEPOIS DE CALCULAR O DT!
  encoderLeft.clearCount();   
  encoderRight.clearCount();

  // DELTA de distância neste ciclo
  newLeft   = CountLeft  * METERS_PER_COUNT;
  newRight  = CountRight * METERS_PER_COUNT;
  newCenter = (newLeft + newRight) / 2.0;

  // Velocidades reais para o PID (m/s)
  linearVel  = newCenter / dt;
  angularVel = ((newRight - newLeft) / WHEEL_LR_DISTANCE) / dt;

  // Acúmulo de posição para o EKF/SLAM
  theta = theta + ((newRight - newLeft) / WHEEL_LR_DISTANCE);
  posX = posX + (newCenter * cos(theta));
  posY = posY + (newCenter * sin(theta));

  // Preencher mensagem
  int64_t ns = rmw_uros_epoch_nanos();
  encoder_msg.header.stamp.sec = (int32_t)(ns / 1000000000LL);
  encoder_msg.header.stamp.nanosec = (uint32_t)(ns % 1000000000LL);
  
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
  // encoder_msg.twist.twist.linear.y = input_left; // Para debug de Encoders
  // encoder_msg.twist.twist.linear.z = input_right;
  
  encoder_msg.twist.twist.angular.x = 0.0;
  encoder_msg.twist.twist.angular.y = 0.0;
  encoder_msg.twist.twist.angular.z = angularVel;

  rcl_ret_t ret = rcl_publish(&encoder_pub, &encoder_msg, NULL);

  if (ret != RCL_RET_OK) {
    // mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
    // mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
    // mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
    // mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
  }
}

void callback_imu(){
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Preencher timestamp
  int64_t ns = rmw_uros_epoch_nanos();
  imu_msg.header.stamp.sec = (int32_t)(ns / 1000000000LL);
  imu_msg.header.stamp.nanosec = (uint32_t)(ns % 1000000000LL);

  // Acelerômetro (m/s²)
  imu_msg.linear_acceleration.x = a.acceleration.x;
  imu_msg.linear_acceleration.y = a.acceleration.y;
  imu_msg.linear_acceleration.z = a.acceleration.z;

  // Giroscópio (rad/s)
  imu_msg.angular_velocity.x = g.gyro.x;
  imu_msg.angular_velocity.y = g.gyro.y;
  imu_msg.angular_velocity.z = g.gyro.z;

  // Publicar
  rcl_ret_t ret = rcl_publish(&imu_pub, &imu_msg, NULL);

  if (ret != RCL_RET_OK) {

  }
}

//=============================================================================
//                        FUNÇÕES AUXILIARES
void callback_battery(rcl_timer_t * timer, int64_t last_call_time){
  if (timer == NULL) return;

  float raw1 = analogRead(VOLTAGE1_PIN);
  float voltage1 = raw1 * (3.3f / 4095.1f) * VOLTAGE_RATIO;

  float raw2 = analogRead(VOLTAGE2_PIN);
  float voltage2 = raw2 * (3.3f / 4095.1f) * VOLTAGE_RATIO;

  battery_msg.cell_voltage.data[0] = voltage1;
  battery_msg.cell_voltage.data[1] = voltage2;
  battery_msg.cell_voltage.size = 2;
  battery_msg.voltage = voltage1 + voltage2;

  int64_t ns = rmw_uros_epoch_nanos();
  battery_msg.header.stamp.sec = (int32_t)(ns / 1000000000LL);
  battery_msg.header.stamp.nanosec = (uint32_t)(ns % 1000000000LL);

  rcl_ret_t ret = rcl_publish(&battery_pub, &battery_msg, NULL);

  if (ret != RCL_RET_OK) {

  }
}

//=============================================================================
//                          FUNÇÃO PRINCIPAL

void callback_watchdog(rcl_timer_t * timer, int64_t last_call_time){
  if (timer == NULL) return;

  if (millis() - watchdog_cmdvel >= CMD_TIMEOUT_MS){
    targetleftVel  = 0.0;
    targetrightVel = 0.0;
    pidLeft.Reset();
    pidRight.Reset();
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
    mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
  }

  callback_encoder();
  callback_imu();
  callback_motorcontrol();
}

//==============================================================
//                              SETUP

void setup() {
  Serial.begin(921600); // 921600 Para permitir corretamente todos os dados para serem passados rapidamente

  // CONFIGURAÇÕES
  set_microros_serial_transports(Serial);
  delay(500);

  // ENCODER
  ESP32Encoder::useInternalWeakPullResistors = UP;
  encoderLeft.attachFullQuad(ENCODER_LEFT_A, ENCODER_LEFT_B);
  encoderRight.attachFullQuad(ENCODER_RIGHT_A, ENCODER_RIGHT_B);

  encoderLeft.clearCount();
  encoderRight.clearCount();

  // IMU - Inicializar MPU6050
  if (!mpu.begin()) {
    while (1) {
      delay(10);
    }
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // MCPWM (Modulo PWN Física da ESP32)
  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, MOTOR_LEFT_RPWM);
  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, MOTOR_LEFT_LPWM);
  mcpwm_gpio_init(MCPWM_UNIT_1, MCPWM0A, MOTOR_RIGHT_RPWM);
  mcpwm_gpio_init(MCPWM_UNIT_1, MCPWM0B, MOTOR_RIGHT_LPWM);

  mcpwm_config_t pwm_config;
  pwm_config.frequency = 20000;
  pwm_config.cmpr_a = 0;
  pwm_config.cmpr_b = 0;
  pwm_config.counter_mode = MCPWM_UP_COUNTER;
  pwm_config.duty_mode = MCPWM_DUTY_MODE_0;

  mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
  mcpwm_init(MCPWM_UNIT_1, MCPWM_TIMER_0, &pwm_config);

  pinMode(MOTOR_EN, OUTPUT);
  digitalWrite(MOTOR_EN, HIGH);
  
  // PID COnfiguration -> Set: TIMER mode (Chamado por TIMER externo)
  pidLeft.SetMode(QuickPID::Control::timer);
  pidLeft.SetOutputLimits(-100.0, 100.0);  // Porcentagem
  pidLeft.SetSampleTimeUs(20000);          // 20ms = 50Hz
  
  pidRight.SetMode(QuickPID::Control::timer);
  pidRight.SetOutputLimits(-100.0, 100.0);
  pidRight.SetSampleTimeUs(20000);

  // Battery Control Config
  pinMode(VOLTAGE1_PIN, INPUT);
  pinMode(VOLTAGE2_PIN, INPUT);

  // Inicialização das Variáveis do Tempo
  timehelper = millis();
  watchdog_cmdvel = millis();

  // Setup microROS
  allocator = rcl_get_default_allocator();
  ros_domain = 77;

  rmw_qos_profile_t cmd_vel_qos = rmw_qos_profile_sensor_data;
  cmd_vel_qos.depth = 1;

  init_options = rcl_get_zero_initialized_init_options();
  rcl_init_options_init(&init_options, allocator);
  rcl_init_options_set_domain_id(&init_options, ros_domain);
  
  rmw_uros_sync_session(1000);
  if (!rmw_uros_epoch_synchronized()) {
    // Em caso de falhas —
  }
  
  rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator);
  rclc_node_init_default(&node, "esp32_imu", "", &support);

  sensor_msgs__msg__BatteryState__init(&battery_msg);
  nav_msgs__msg__Odometry__init(&encoder_msg);
  sensor_msgs__msg__Imu__init(&imu_msg);

  // Setup das Mensagens - Precisa inicializar na ordem correta
  encoder_msg.header.frame_id.data = (char *)"odom";
  encoder_msg.header.frame_id.size = strlen("odom");
  encoder_msg.header.frame_id.capacity = encoder_msg.header.frame_id.size + 1;

  encoder_msg.child_frame_id.data = (char *)"robot_footprint";
  encoder_msg.child_frame_id.size = strlen("robot_footprint");
  encoder_msg.child_frame_id.capacity = encoder_msg.child_frame_id.size + 1;

  imu_msg.header.frame_id.data = (char *)"imu_link";
  imu_msg.header.frame_id.size = strlen("imu_link");
  imu_msg.header.frame_id.capacity = strlen("imu_link") + 1;

  imu_msg.orientation_covariance[0] = -1.0;

  battery_msg.present = true;
  battery_msg.power_supply_status = sensor_msgs__msg__BatteryState__POWER_SUPPLY_STATUS_DISCHARGING;
  battery_msg.power_supply_health = sensor_msgs__msg__BatteryState__POWER_SUPPLY_HEALTH_GOOD;
  battery_msg.power_supply_technology = sensor_msgs__msg__BatteryState__POWER_SUPPLY_TECHNOLOGY_VRLA;

  static float cell_data[2];                                  //Verificar se estas linhas são necessárias
  battery_msg.cell_voltage.data = cell_data;
  battery_msg.cell_voltage.capacity = 2;
  battery_msg.cell_voltage.size = 0;

  rclc_publisher_init_default(
    &encoder_pub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry),
    ODOM_TOPIC
  );

  rclc_publisher_init_default(
    &imu_pub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
    IMU_TOPIC
  );

  rclc_publisher_init_default(
    &battery_pub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, BatteryState),
    BATTERY_TOPIC
  );

  rclc_subscription_init(
    &cmd_vel_sub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    CMD_VEL_TOPIC,
    &cmd_vel_qos
  );

  // Timer e Executor
  rclc_timer_init_default2(&timer_watchdog, &support, RCL_MS_TO_NS(WATCHDOG_PUBLISH_RATE), callback_watchdog, true);
  rclc_timer_init_default2(&timer_battery, &support, RCL_MS_TO_NS(BATTERY_PUBLISH_RATE), callback_battery, true);
  rclc_executor_init(&executor, &support.context, 3, &allocator);
  rclc_executor_add_timer(&executor, &timer_watchdog);
  rclc_executor_add_timer(&executor, &timer_battery);
  rclc_executor_add_subscription(&executor, &cmd_vel_sub, &cmd_vel_msg, &callback_cmd_vel, ON_NEW_DATA);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
}