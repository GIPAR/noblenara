/**
 * @file noblenara_config.h
 * @brief Configuration file for Noblenara Wheelchair Project
 * @details ROS2 Jazzy + micro-ROS on ESP32-WROOM-32
 *
 * Hardware:
 * - ESP32-WROOM-32 DevKit
 * - 2x ZKP3808 Encoders (600 PPR, quadrature = 2400 counts/rev)
 * - MPU6050 IMU
 * - 2x BTS7960 H-Bridge Motor Controllers
 * - Ottobock B400 Wheelchair Base
 */

#ifndef NOBLENARA_CONFIG_H
#define NOBLENARA_CONFIG_H

//=============================================================================
// DIMENSÕES DO ROBÔ - [METROS]
//=============================================================================
#define WHEEL_DIAMETER 0.350
#define WHEEL_RADIUS (WHEEL_DIAMETER / 2.0)
#define WHEEL_LR_DISTANCE 0.51

#define WHEEL_CIRCUMFERENCE (3.14159265359 * WHEEL_DIAMETER)
#define METERS_PER_COUNT (WHEEL_CIRCUMFERENCE / COUNTS_PER_REV)

//=============================================================================
// CONFIGURAÇÕES DO ENCONDER
//=============================================================================
#define ENCODER_LEFT_A 33
#define ENCODER_LEFT_B 32
#define ENCODER_RIGHT_A 34
#define ENCODER_RIGHT_B 35

#define COUNTS_PER_REV 2400
#define ENCODER_PPR 600

//=============================================================================
// CONFIGURAÇÕES DO MOTOR
//=============================================================================
#define PWM_MAX 100
#define PWM_MIN -PWM_MAX

#define MOTOR_LEFT_LPWM 26
#define MOTOR_LEFT_RPWM 25
#define MOTOR_EN 23
#define MOTOR_RIGHT_LPWM 27
#define MOTOR_RIGHT_RPWM 14

#define K_P 30.0  // P
#define K_I 0.0   // I
#define K_D 0.3   // D

//=============================================================================
// CONFIGURAÇÕES DA BATERIA
//=============================================================================
#define VOLTAGE_RATIO (4.85 * (4.85 / 3.3))
#define VOLTAGE1_PIN 13
#define VOLTAGE2_PIN 12

//=============================================================================
// CONFIGURAÇÕES MICRO-ROS
//=============================================================================
// #define MICRO_ROS_AGENT_IP    "192.168.1.100"
#define MICRO_ROS_AGENT_PORT 8888

// Taxas de Publicação (ms)
#define WATCHDOG_PUBLISH_RATE 20
#define BATTERY_PUBLISH_RATE 1000

// ROS Topic names
#define ODOM_TOPIC "/noblenara/odom"
#define IMU_TOPIC "/noblenara/imu/data"
#define CMD_VEL_TOPIC "/noblenara/cmd_vel"
#define BATTERY_TOPIC "/noblenara/battery_status"

// Timeout do Robô
#define CMD_TIMEOUT_MS 500

#endif
