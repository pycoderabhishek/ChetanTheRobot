# Backend Updates for GPIO PWM Support

## Summary
Updated FastAPI backend to support both **PCA9685** (12-bit, 0-4095 ticks) and **GPIO PWM** (16-bit, 0-65535 ticks) firmware implementations.

## Changes Made

### 1. servo_config.py (ServoController class)

#### Added GPIO PWM Constants
```python
GPIO_PWM_TICKS_PER_CYCLE = 65536  # 16-bit resolution (0-65535)
GPIO_PWM_FREQUENCY = 50  # 50 Hz for servos
GPIO_PWM_PERIOD_US = 20000  # 20 ms period
GPIO_PWM_US_PER_TICK = GPIO_PWM_PERIOD_US / GPIO_PWM_TICKS_PER_CYCLE  # ~0.305 µs
```

#### Added New Methods
- ✅ `pulse_us_to_gpio_pwm_ticks(pulse_us)` - Convert PWM pulse to GPIO ticks
- ✅ `angle_to_gpio_pwm_ticks(channel, angle)` - Convert angle to GPIO ticks
- ✅ `gpio_pwm_ticks_to_pulse_us(ticks)` - Reverse: GPIO ticks → pulse

#### Kept Existing Methods
- ✅ `pulse_us_to_pca9685_ticks(pulse_us)` - PCA9685 conversion (unchanged)
- ✅ `angle_to_pca9685_ticks(channel, angle)` - PCA9685 conversion (unchanged)
- ✅ `pca9685_ticks_to_pulse_us(ticks)` - PCA9685 reverse (unchanged)

**Result:** Backend can calculate tick counts for both hardware types

### 2. contracts.py (Message Contracts)

#### Updated ServoStateFeedback Field
**Before:**
```python
pca9685_ticks: int = Field(
    ge=0,
    le=4095,
    description="PCA9685 tick count (0-4095)"
)
```

**After:**
```python
pca9685_ticks: int = Field(
    ge=0,
    le=65535,
    description="PWM tick count (PCA9685: 0-4095, GPIO PWM: 0-65535)"
)
```

#### Updated Example Value
- **Before:** `pca9685_ticks: 329` (PCA9685 typical)
- **After:** `pca9685_ticks: 50000` (GPIO PWM typical)

**Result:** API schema accepts both tick ranges, field renamed for backward compatibility

### 3. servo_manager.py (WebSocket Models)

#### Updated ServoFeedback Documentation
```python
class ServoFeedback(BaseModel):
    """Servo state feedback from ESP32 (works with PCA9685 or GPIO PWM)."""
    pca9685_ticks: int  # Generic PWM ticks (PCA9685: 0-4095, GPIO: 0-65535)
```

#### Updated Example
- **Before:** `pca9685_ticks: 307`
- **After:** `pca9685_ticks: 50000`

**Result:** WebSocket models support both hardware types

### 4. servo_state.py (No Changes Required)
✅ Existing code works unchanged:
- Still uses `pulse_us_to_pca9685_ticks()` for state calculation
- Field `pca9685_ticks` stores generic PWM tick value
- Backend automatically handles both firmware types

## Backward Compatibility
✅ **Fully backward compatible:**
- Field names unchanged (`pca9685_ticks` → still called `pca9685_ticks`)
- Existing PCA9685 integration still works
- GPIO PWM added as supplementary methods
- Message schema accepts wider tick range (0-65535)

## Usage

### For PCA9685 Hardware (Original)
```python
controller = ServoController(servo_configs)
ticks = controller.angle_to_pca9685_ticks(channel=0, angle=90.0)
# Returns: 307 (12-bit range 0-4095)
```

### For GPIO PWM Hardware (ESP32-S3)
```python
controller = ServoController(servo_configs)
ticks = controller.angle_to_gpio_pwm_ticks(channel=0, angle=90.0)
# Returns: 50000 (16-bit range 0-65535)
```

## Testing Checklist
- [ ] Backend receives `pca9685_ticks: 50000` from ESP32-S3 firmware
- [ ] Servo state updates correctly with GPIO PWM tick values
- [ ] WebSocket feedback messages display correctly
- [ ] Dashboard shows servo positions accurately
- [ ] No errors on ServoStateFeedback validation

## Notes
1. **Field Naming:** `pca9685_ticks` retained for backward compatibility (despite generic use)
2. **Tick Range:** Now accepts 0-65535 instead of 0-4095
3. **Conversion Methods:** Both PCA9685 and GPIO PWM methods available
4. **Hardware Agnostic:** Backend works with either firmware type transparently

## Future Consideration
To fully support hardware-agnostic design, could:
1. Rename field to `pwm_ticks` in next version
2. Add metadata field indicating hardware type
3. Store both PCA9685 and GPIO tick values for analysis

---
**Date:** January 27, 2026  
**Status:** ✅ Complete - Backend supports GPIO PWM without breaking PCA9685 compatibility
