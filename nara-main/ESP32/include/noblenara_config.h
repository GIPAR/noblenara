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
// ROBOT DIMENSIONS
//=============================================================================

#define WHEEL_DIAMETER 0.336 // Wheel diameter in meters (33.6 cm)
#define WHEEL_RADIUS (WHEEL_DIAMETER / 2.0)
#define WHEEL_LR_DISTANCE 0.51 // Distance between left and right wheels in meters (51 cm)

#define WHEEL_CIRCUMFERENCE (3.14159265359 * WHEEL_DIAMETER)    // meters
#define METERS_PER_COUNT (WHEEL_CIRCUMFERENCE / COUNTS_PER_REV) // ~0.00044 m/count

//=============================================================================
// ENCODER CONFIGURATION - Encoder is expected to be 21 and 22 already, no need to declare
//=============================================================================

#define ENCODER_LEFT_A 33  // Left encoder Channel A
#define ENCODER_LEFT_B 32  // Left encoder Channel B
#define ENCODER_RIGHT_A 34 // Right encoder Channel A
#define ENCODER_RIGHT_B 35 // Right encoder Channel B

#define COUNTS_PER_REV 2400 // Total counts per revolution (with 4x quadrature)
#define ENCODER_PPR 600     // Native pulses per revolution (CPR/4) || CHECK!

//=============================================================================
// MOTOR CONFIGURATION
//=============================================================================

#define PWM_MAX 100
#define PWM_MIN -PWM_MAX

#define MOTOR_LEFT_LPWM 19
#define MOTOR_LEFT_RPWM 18
#define MOTOR_EN 23 //Com todos os quatro enable juntos
#define MOTOR_RIGHT_LPWM 27
#define MOTOR_RIGHT_RPWM 14

#define K_P 30.0  // P constant
#define K_I 0.0   // I constant
#define K_D 0.3   // D constant

//=============================================================================
// MICRO-ROS CONFIGURATION
//=============================================================================

// #define MICRO_ROS_AGENT_IP    "192.168.1.100"  // TODO: Update with Jetson IP
#define MICRO_ROS_AGENT_PORT 8888 // Default micro-ROS agent port

// Publishing rates (Hz)
#define WATCHDOG_PUBLISH_RATE 20 // Odometry publishing frequency, change later
#define IMU_PUBLISH_RATE 20  // IMU data publishing frequency, change later

// ROS Topic names
#define ODOM_TOPIC "/noblenara/odom"
#define IMU_TOPIC "/noblenara/imu/data"
#define CMD_VEL_TOPIC "/noblenara/cmd_vel"

// Command timeout for safety
#define CMD_TIMEOUT_MS 500 // Stop motors if no command received for 500ms, change the time later if needed

#endif