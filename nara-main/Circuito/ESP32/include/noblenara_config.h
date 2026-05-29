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
// DIMENSIONS
//=============================================================================
#define WHEEL_DIAMETER 0.336   // Diâmetro da roda em metros (33.6 cm)
#define WHEEL_RADIUS (WHEEL_DIAMETER / 2.0)
#define WHEEL_LR_DISTANCE 0.51 // Distância entre as rodas anteriores em metros (51 cm)

#define WHEEL_CIRCUMFERENCE (3.14159265359 * WHEEL_DIAMETER)    // metros
#define METERS_PER_COUNT (WHEEL_CIRCUMFERENCE / COUNTS_PER_REV) // ~0.00044 m/count

//=============================================================================
// ENCODER CONFIGURATIONS
//=============================================================================
#define ENCODER_LEFT_A 32  // Left encoder Channel A
#define ENCODER_LEFT_B 33  // Left encoder Channel B
#define ENCODER_RIGHT_A 34 // Right encoder Channel A
#define ENCODER_RIGHT_B 35 // Right encoder Channel B

#define COUNTS_PER_REV 2400 // Counts por Revolução (com 4x quadratura)
#define ENCODER_PPR 600     // Pulsos nativos por revolução (CPR/4)

//=============================================================================
// MOTOR CONFIGURATION
//=============================================================================
#define PWM_MAX 100
#define PWM_MIN -PWM_MAX

#define MOTOR_LEFT_LPWM 26
#define MOTOR_LEFT_RPWM 25
#define MOTOR_EN 23         // Todos os 4 Enables estão conectados na fiação
#define MOTOR_RIGHT_LPWM 27
#define MOTOR_RIGHT_RPWM 14

#define K_P 30.0  // P
#define K_I 0.0   // I
#define K_D 0.3   // D

//=============================================================================
// BATTERY CONTROL CONFIGURATION
//=============================================================================
#define VOLTAGE_RATIO (4.85 * (4.85 / 3.3)) //Testado uma vez e deu esta ratio de tensão, mas originalmente é 5
#define VOLTAGE1_PIN 13
#define VOLTAGE2_PIN 18

//=============================================================================
// MICRO-ROS CONFIGURATION
//=============================================================================
// #define MICRO_ROS_AGENT_IP    "192.168.1.100"  // TODO: Atualizar com IP da Jetson
#define MICRO_ROS_AGENT_PORT 8888 // Default micro-ROS agent port

// Publishing rates; milisegundos)
#define WATCHDOG_PUBLISH_RATE 20
#define IMU_PUBLISH_RATE 20
#define BATTERY_PUBLISH_RATE 1000

// ROS Topic names
#define ODOM_TOPIC "/noblenara/odom"
#define IMU_TOPIC "/noblenara/imu/data"
#define CMD_VEL_TOPIC "/noblenara/cmd_vel"
#define BATTERY_TOPIC "/noblenara/battery_status"

// Timeout do Robô
#define CMD_TIMEOUT_MS 500 // Para os motores pelo código caso último comando seja após "...ms"

#endif
