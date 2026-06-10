#!/usr/bin/env python3

"""
test_hardware.py - SNATCH3R Hardware Verification Script
=========================================================
Run this BEFORE snatch3r.py to confirm all motors and sensors
are wired correctly and responding as expected.

Deploy:
    scp test_hardware.py robot@ev3dev.local:/home/robot/SNATCH3R/
    ssh robot@ev3dev.local "python3 /home/robot/SNATCH3R/test_hardware.py"

After running, copy/paste ALL output back to Claude for review.
Each test prints PASS, FAIL, or WARN with details.
"""

import time
import sys
from time import sleep

# == Imports ===================================================
print("=" * 55)
print("SNATCH3R HARDWARE TEST")
print("=" * 55)
print()

# Test ev3dev2 import first - if this fails nothing else will work
print("[0] LIBRARY IMPORT")
try:
    from ev3dev2.motor import (OUTPUT_A, OUTPUT_B, OUTPUT_C,
                                MediumMotor, LargeMotor, MoveTank,
                                SpeedPercent)
    from ev3dev2.sensor import INPUT_1, INPUT_4
    from ev3dev2.sensor.lego import TouchSensor, InfraredSensor
    from ev3dev2.button import Button
    from ev3dev2.sound import Sound
    from ev3dev2.display import Display
    print("  PASS - ev3dev2 imported successfully")
except ImportError as e:
    print("  FAIL - ev3dev2 import failed: %s" % e)
    print("  Cannot continue. Is ev3dev running? Is this the EV3?")
    sys.exit(1)

print()
results = []   # collect (test_name, status, detail) tuples


# == Helper ====================================================

def log_result(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    tag = "  %s - %s" % (status, name)
    if detail:
        tag += ": %s" % detail
    print(tag)
    results.append((name, status, detail))


# == Test 1: Motor Detection ===================================
print("[1] MOTOR DETECTION")
print("    Checking all 3 motors are connected to correct ports...")

try:
    arm_motor = MediumMotor(OUTPUT_A)
    pos = arm_motor.position  # live read confirms it responds
    log_result("OUTPUT_A MediumMotor (arm)", True,
               "connected, position=%d" % pos)
except Exception as e:
    log_result("OUTPUT_A MediumMotor (arm)", False, str(e))
    arm_motor = None

try:
    left_motor = LargeMotor(OUTPUT_B)
    pos = left_motor.position
    log_result("OUTPUT_B LargeMotor (left track)", True,
               "connected, position=%d" % pos)
except Exception as e:
    log_result("OUTPUT_B LargeMotor (left track)", False, str(e))
    left_motor = None

try:
    right_motor = LargeMotor(OUTPUT_C)
    pos = right_motor.position
    log_result("OUTPUT_C LargeMotor (right track)", True,
               "connected, position=%d" % pos)
except Exception as e:
    log_result("OUTPUT_C LargeMotor (right track)", False, str(e))
    right_motor = None

print()


# == Test 2: Sensor Detection ==================================
print("[2] SENSOR DETECTION")
print("    Checking Touch Sensor (port 1) and IR Sensor (port 4)...")

try:
    touch_sensor = TouchSensor(INPUT_1)
    state = touch_sensor.is_pressed  # live read
    log_result("INPUT_1 TouchSensor", True,
               "connected, is_pressed=%s" % state)
except Exception as e:
    log_result("INPUT_1 TouchSensor", False, str(e))
    touch_sensor = None

try:
    ir_sensor = InfraredSensor(INPUT_4)
    prox = ir_sensor.proximity  # live read
    log_result("INPUT_4 InfraredSensor", True,
               "connected, proximity=%d" % prox)
except Exception as e:
    log_result("INPUT_4 InfraredSensor", False, str(e))
    ir_sensor = None

print()


# == Test 3: Motor Position Sensor Reset =======================
print("[3] MOTOR ROTATION SENSOR RESET")
print("    Verifying motor position encoders can be read and reset...")

if right_motor:
    try:
        pos_before = right_motor.position
        right_motor.reset()
        pos_after = right_motor.position
        log_result("Motor C (right) reset",
                   pos_after == 0,
                   "before=%d after=%d (expected 0)" % (pos_before, pos_after))
    except Exception as e:
        log_result("Motor C (right) reset", False, str(e))
else:
    log_result("Motor C (right) reset", False, "motor not connected, skipped")

if arm_motor:
    try:
        arm_motor.reset()
        log_result("Motor A (arm) reset",
                   arm_motor.position == 0,
                   "position after reset=%d" % arm_motor.position)
    except Exception as e:
        log_result("Motor A (arm) reset", False, str(e))
else:
    log_result("Motor A (arm) reset", False, "motor not connected, skipped")

print()


# == Test 4: Touch Sensor Live Reading ========================
print("[4] TOUCH SENSOR LIVE READING")
print("    Reading touch sensor state (DO NOT press it during this test)...")

if touch_sensor:
    try:
        state = touch_sensor.is_pressed
        log_result("Touch sensor unpressed read",
                   state == False,
                   "is_pressed=%s (expected False - do not press it)" % state)
    except Exception as e:
        log_result("Touch sensor read", False, str(e))
else:
    log_result("Touch sensor read", False, "sensor not connected, skipped")

print()


# == Test 5: IR Sensor Proximity ===============================
print("[5] IR SENSOR PROXIMITY")
print("    Reading proximity (0=close, 100=far or nothing)...")
print("    No beacon needed for this test.")

if ir_sensor:
    try:
        prox = ir_sensor.proximity
        # Any reading 0-100 is valid
        valid = (0 <= prox <= 100)
        log_result("IR proximity read",
                   valid,
                   "proximity=%d (0=close 100=far)" % prox)
    except Exception as e:
        log_result("IR proximity read", False, str(e))
else:
    log_result("IR proximity read", False, "sensor not connected, skipped")

print()


# == Test 6: IR Sensor Beacon Mode =============================
print("[6] IR SENSOR BEACON MODE")
print("    IMPORTANT: Activate beacon on your IR remote NOW.")
print("    Press and HOLD the top button on the IR remote.")
print("    Hold it ~30cm (1 foot) in front of the IR sensor.")
print("    Waiting 5 seconds for you to do this...")
sleep(5)

if ir_sensor:
    try:
        # Correct API: separate heading() and distance() calls
        heading  = ir_sensor.heading(channel=1)
        distance = ir_sensor.distance(channel=1)
        log_result("ir_sensor.heading(channel=1)",
                   True,
                   "heading=%s (expected -25 to 25, None=no beacon)" % heading)
        log_result("ir_sensor.distance(channel=1)",
                   True,
                   "distance=%s (expected 0 to 100, None=no beacon)" % distance)

    except Exception as e:
        log_result("ir_sensor.heading/distance",
                   False,
                   "Error: %s" % e)
else:
    log_result("IR beacon mode", False, "sensor not connected, skipped")

print()


# == Test 7: Motor A (arm) short movement ======================
print("[7] ARM MOTOR MOVEMENT")
print("    Moving arm motor A forward briefly (1 second at 20% speed).")
print("    Watch the arm - it should move slightly forward.")
print("    WARNING: Hold the arm gently if it is already raised.")
print("    Starting in 3 seconds...")
sleep(3)

if arm_motor:
    try:
        arm_motor.reset()
        pos_start = arm_motor.position
        arm_motor.on_for_seconds(SpeedPercent(20), 1, brake=False)
        sleep(0.2)
        pos_end = arm_motor.position
        moved = abs(pos_end - pos_start) > 10  # should have moved > 10 degrees
        log_result("Arm motor forward movement",
                   moved,
                   "start=%d end=%d delta=%d (expected >10)" % (
                       pos_start, pos_end, pos_end - pos_start))
    except Exception as e:
        log_result("Arm motor forward movement", False, str(e))
else:
    log_result("Arm motor forward movement", False, "motor not connected, skipped")

print()


# == Test 8: Drive motors short movement =======================
print("[8] DRIVE MOTOR MOVEMENT")
print("    Moving BOTH track motors briefly (1 second at 20% forward).")
print("    Robot should roll forward slightly.")
print("    Make sure robot is on a flat surface with space in front.")
print("    Starting in 3 seconds...")
sleep(3)

if left_motor and right_motor:
    try:
        tank = MoveTank(OUTPUT_B, OUTPUT_C)
        left_motor.reset()
        right_motor.reset()
        pos_b_start = left_motor.position
        pos_c_start = right_motor.position

        tank.on_for_seconds(SpeedPercent(20), SpeedPercent(20), 1, brake=True)
        sleep(0.2)

        pos_b_end = left_motor.position
        pos_c_end = right_motor.position
        delta_b = abs(pos_b_end - pos_b_start)
        delta_c = abs(pos_c_end - pos_c_start)

        both_moved = delta_b > 10 and delta_c > 10
        log_result("Left motor (B) moved",
                   delta_b > 10,
                   "start=%d end=%d delta=%d" % (pos_b_start, pos_b_end, delta_b))
        log_result("Right motor (C) moved",
                   delta_c > 10,
                   "start=%d end=%d delta=%d" % (pos_c_start, pos_c_end, delta_c))

        # Check if motors moved roughly the same amount (straight line)
        ratio = min(delta_b, delta_c) / max(delta_b, delta_c) if max(delta_b, delta_c) > 0 else 0
        log_result("Motors moved symmetrically (straight line)",
                   ratio > 0.8,
                   "ratio=%.2f (B=%d C=%d, expected >0.8)" % (ratio, delta_b, delta_c))
    except Exception as e:
        log_result("Drive motor movement", False, str(e))
else:
    log_result("Drive motor movement", False, "one or both motors not connected, skipped")

print()


# == Test 9: Touch sensor press detection ======================
print("[9] TOUCH SENSOR PRESS TEST")
print("    Press the Touch Sensor on the robot NOW and hold it.")
print("    Waiting 5 seconds - press it during this window...")
sleep(2)

if touch_sensor:
    pressed_detected = False
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if touch_sensor.is_pressed:
            pressed_detected = True
            break
        sleep(0.05)
    log_result("Touch sensor press detected",
               pressed_detected,
               "detected=%s (you had 5 seconds to press it)" % pressed_detected)
else:
    log_result("Touch sensor press detection", False, "sensor not connected, skipped")

print()


# == Summary ===================================================
print("=" * 55)
print("RESULTS SUMMARY")
print("=" * 55)

passed = [r for r in results if r[1] == "PASS"]
failed = [r for r in results if r[1] == "FAIL"]

for name, status, detail in results:
    print("  %-6s %s" % (status, name))

print()
print("  Total: %d  |  Passed: %d  |  Failed: %d" % (
    len(results), len(passed), len(failed)))

if failed:
    print()
    print("FAILED TESTS - copy these to Claude:")
    for name, status, detail in failed:
        print("  FAIL - %s: %s" % (name, detail))

print()
print("Copy ALL output above and paste to Claude for review.")
print("=" * 55)