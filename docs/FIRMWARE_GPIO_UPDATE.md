# AMHR-PD Firmware GPIO PWM Update

## Summary
Successfully updated firmware from PCA9685 I2C PWM driver to **direct GPIO PWM** on ESP32-S3.

## Key Changes

### 1. Hardware Configuration
- **Removed:** PCA9685 I2C communication (GPIO 8/9)
- **Added:** Direct ESP32-S3 LEDC PWM on GPIO pins

### 2. GPIO Pin Mapping (MANDATORY)
```
Servo 0 → GPIO 4   (ledcChannel 0)
Servo 1 → GPIO 5   (ledcChannel 1)
Servo 2 → GPIO 6   (ledcChannel 2)
Servo 3 → GPIO 7   (ledcChannel 3)
Servo 4 → GPIO 15  (ledcChannel 4)
Servo 5 → GPIO 16  (ledcChannel 5)
Servo 6 → GPIO 17  (ledcChannel 6)
Servo 7 → GPIO 18  (ledcChannel 7)
Servo 8 → GPIO 8   (ledcChannel 8)
Servo 9 → GPIO 9   (ledcChannel 9)
```

### 3. PWM Configuration
- **Frequency:** 50 Hz (standard servo control)
- **Period:** 20 ms (20,000 microseconds)
- **Resolution:** 16-bit (0–65535 ticks)
- **Pulse Range:** 1000–2000 microseconds (0–180°)

### 4. Removed Dependencies
- ❌ `#include <Wire.h>` (I2C communication)
- ❌ `#include <Adafruit_PWMServoDriver.h>` (PCA9685 library)
- ❌ All I2C initialization code
- ❌ PCA9685-specific timing constants

### 5. Added Functions & Methods
- ✅ `setup_gpio_pwm()` - Initialize LEDC channels on GPIO pins
- ✅ `ledcSetup(ch, frequency, resolution)` - Configure PWM frequency/resolution
- ✅ `ledcAttachPin(gpio, channel)` - Attach LEDC channel to GPIO
- ✅ `ledcWrite(channel, ticks)` - Write PWM value to servo

### 6. Updated Servo Control Logic

#### Direct Angle to PWM Conversion
```cpp
int pulse_us = SERVO_MIN_PULSE_US + (angle / 180.0) * (SERVO_MAX_PULSE_US - SERVO_MIN_PULSE_US);
uint16_t pwm_ticks = (pulse_us * 65535) / 20000;
ledcWrite(channel, pwm_ticks);
```

#### Servo State Structure
- Changed: `pca9685_ticks` → `pwm_ticks` (16-bit GPIO PWM ticks)

#### Feedback Messages
- Now reports GPIO PWM ticks instead of PCA9685 ticks
- Maintains same pulse width and angle information

### 7. File Changes

#### amhrpd_firmware.ino
- Updated header documentation
- Removed PCA9685 #includes
- Added SERVO_PINS array with GPIO mapping
- Replaced `setup_pca9685()` with `setup_gpio_pwm()`
- Updated `handle_servo_command()` to use `ledcWrite()`
- Updated `send_servo_feedback()` to calculate GPIO PWM ticks
- Removed `servo_controller.begin()` call (not needed for GPIO PWM)

#### servo_config.h
- Updated documentation for GPIO PWM
- Replaced PCA9685 constants with GPIO PWM constants:
  - `GPIO_PWM_RESOLUTION_BITS = 16`
  - `GPIO_PWM_MAX_TICKS = 65535`
- Updated `ServoState` structure: `pca9685_ticks` → `pwm_ticks`
- Removed PCA9685-specific methods:
  - ❌ `pulseUsToPca9685Ticks()`
  - ❌ `angleToPca9685Ticks()`
  - ❌ `pca9685TicksToPulseUs()`
- Added GPIO PWM methods:
  - ✅ `pulseUsToGpioPwmTicks()`
  - ✅ `angleToGpioPwmTicks()`
  - ✅ `gpioPwmTicksToPulseUs()`

## Library Requirements
**Before:** ArduinoWebSockets, ArduinoJson, Adafruit_PWMServoDriver  
**After:** ArduinoWebSockets, ArduinoJson (only)

## Testing Checklist
- [ ] Firmware compiles without errors
- [ ] All 10 servos initialize to 90° (home position)
- [ ] Backend commands received and executed
- [ ] Servo feedback reported correctly
- [ ] WebSocket registration succeeds
- [ ] GPIO pins 4-9, 15-18 output correct PWM signals

## Hardware Setup
1. Connect servo signals to ESP32-S3 GPIO pins (see mapping above)
2. Connect servo power (6V) to common power rail
3. Connect servo ground to ESP32-S3 ground
4. Connect external 6V power supply (≥20A) to servo power
5. No I2C or PCA9685 hardware required

## Voltage Compatibility
- ESP32-S3 GPIO outputs: 3.3V logic
- MG996R servo control: 3.3V logic compatible ✓
- No level shifter required

## Notes
- ServoController class still available for configuration reference
- Angle-to-pulse conversion logic unchanged (remain backward compatible)
- GPIO PWM automatically handles 50 Hz frequency and 20ms period
- All 10 PWM channels can operate independently

---
**Date:** January 27, 2026  
**Status:** ✅ Complete - Ready for compilation and deployment
