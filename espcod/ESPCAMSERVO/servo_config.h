#ifndef SERVO_CONFIG_H
#define SERVO_CONFIG_H

/*
 * SERVO_CONFIG.H
 *
 * ESPCAM + SERVO CONTROL INTEGRATED
 * ESP32-S3 N16R8 | ESP32Servo Library | 10x MG996R
 *
 * GPIO ALLOCATION:
 *   I2S Audio : GPIO 4 (BCLK), 5 (LRC), 6 (DOUT), 7 (DIN)  — reserved, do NOT use for servos
 *   Servo PWM : GPIO 12–21  (currently used; additional safe pins: 35–42, 47, 48)
 *
 * WARNING: ESP32-S3 restricted GPIOs
 *   GPIO 0, 3, 45, 46 = Strapping pins (avoid)
 *   GPIO 26–32         = PSRAM / internal SPI flash (DO NOT USE)
 *   GPIO 6, 7          = Used here for I2S DOUT/DIN — safe on ESP32-S3 N16R8
 *
 * Safe GPIOs for servo PWM: 12–21, 35–42, 47, 48
 */

#include <stdint.h>

/* =======================================================================
   GPIO PIN MAPPING (servo index → GPIO pin)
   All pins are in the 12–21 range, clear of I2S audio (4,5,6,7)
   ======================================================================= */

static const int SERVO_PINS[10] = {
  12,  // CH0 - L_SHOULDER
  13,  // CH1 - L_ELBOW_1
  14,  // CH2 - L_ELBOW_2
  15,  // CH3 - L_GRIPPER
  16,  // CH4 - R_SHOULDER
  17,  // CH5 - R_ELBOW_1
  18,  // CH6 - R_ELBOW_2
  19,  // CH7 - R_GRIPPER
  20,  // CH8 - NECK_UPDOWN
  21   // CH9 - NECK_LEFTRIGHT
};

/* =======================================================================
   SERVO ROLE DEFINITIONS
   ======================================================================= */

// LEFT ARM
#define L_SHOULDER      0
#define L_ELBOW_1       1
#define L_ELBOW_2       2
#define L_GRIPPER       3

// RIGHT ARM
#define R_SHOULDER      4
#define R_ELBOW_1       5
#define R_ELBOW_2       6
#define R_GRIPPER       7

// NECK
#define NECK_UPDOWN     8
#define NECK_LEFTRIGHT  9

/* =======================================================================
   SERVO CONSTANTS (MG996R)
   ======================================================================= */

#define NUM_SERVOS           10
#define SERVO_MIN_PULSE_US   500   // MG996R min pulse
#define SERVO_MAX_PULSE_US   2500  // MG996R max pulse
#define SERVO_MIN_ANGLE      0
#define SERVO_MAX_ANGLE      180
#define SERVO_HOME_ANGLE     90

#endif // SERVO_CONFIG_H
