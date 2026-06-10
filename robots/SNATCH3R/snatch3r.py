#!/usr/bin/env python3

"""
SNATCH3R - Autonomous Robotic Arm
Based DIRECTLY on Chapter 18 of:
  "The LEGO MINDSTORMS EV3 Discovery Book" by Laurens Valk

Translated from Valk's Scratch/EV3-G block programs to ev3dev2 Python.

=== HARDWARE CONFIGURATION (from book, page build step 20) ===
  OUTPUT_A - Medium Motor  (arm + gripper)
  OUTPUT_B - Large Motor   (left track)
  OUTPUT_C - Large Motor   (right track)
  INPUT_1  - Touch Sensor  (detects arm FULLY RAISED - upper limit)
  INPUT_4  - IR Sensor     (proximity + beacon heading + remote)

=== THREE MY BLOCKS (from book pages 39-41) ===
  grab()    - raise arm until Touch Sensor pressed (speed 40%)
  reset()   - grab() then lower 14.2 rotations, reset rotation sensor to 0
  release() - lower arm until rotation sensor == 0

=== AUTONOMOUS SEARCH ALGORITHM (from book pages 46-50) ===
  - Lowest = 26, Position = 0
  - Reset motor C rotation sensor
  - Turn LEFT, loop until motor C > 1800 degrees:
      reading = abs(beacon heading)
      if reading != 0 and reading < Lowest:
          Lowest = reading
          Position = motor C rotation sensor value
          beep
  - Turn RIGHT until motor C rotation sensor <= Position
  - Stop - robot now faces beacon

=== APPROACH (from book page 53) ===
  - Search + drive forward until proximity < 50
  - Then drive forward with steering proportional to heading until proximity < 1
  - Drive forward 1 more rotation to seat IR bug

=== DEPLOY ===
  scp snatch3r.py robot@ev3dev.local:/home/robot/SNATCH3R/
  ssh robot@ev3dev.local "python3 /home/robot/SNATCH3R/snatch3r.py"
"""

import logging
import signal
import time
from threading import Event
from time import sleep

from ev3dev2.motor import (OUTPUT_A, OUTPUT_B, OUTPUT_C,
                           MediumMotor, LargeMotor, MoveTank,
                           MoveSteering, SpeedPercent)
from ev3dev2.sensor import INPUT_1, INPUT_4
from ev3dev2.sensor.lego import TouchSensor, InfraredSensor
from ev3dev2.button import Button
from ev3dev2.display import Display
from ev3dev2.sound import Sound

log = logging.getLogger(__name__)


# -------------------------------------------------------------
#  ARM OPERATIONS  (Valk My Blocks #1, #2, #3)
# -------------------------------------------------------------

def grab(arm_motor, touch_sensor):
    """
    My Block #1: GRAB
    Rotate Medium Motor forward at 40% speed until Touch Sensor is pressed.
    This closes the claws and raises the arm in one continuous motion
    (gravity ensures claws close before arm lifts - see book p.4).
    Brake at End = False (worm gear holds position without power).
    """
    log.info("grab: raising arm until touch sensor pressed")
    arm_motor.on(SpeedPercent(40))
    while not touch_sensor.is_pressed:
        sleep(0.01)
    arm_motor.off(brake=False)
    log.info("grab: touch sensor pressed, arm fully raised")


def reset(arm_motor, touch_sensor):
    """
    My Block #2: RESET  (run at start of every program)
    1. Run grab() to raise arm to known upper boundary (Touch Sensor)
    2. Lower arm backward exactly 14.2 rotations (speed -50%)
    3. Reset rotation sensor to 0
    Result: arm is lowered, claws open, rotation sensor = 0.

    IMPORTANT: claws must be empty during reset (no objects in claws).
    14.2 rotations is only valid when claws were fully closed while raised.
    """
    log.info("reset: starting arm reset sequence")
    grab(arm_motor, touch_sensor)

    # Lower backward 14.2 rotations at 50% speed
    # on_for_rotations with negative speed = reverse direction
    arm_motor.on_for_rotations(SpeedPercent(-50), 14.2, brake=False)

    # Zero the rotation sensor at this lowered position
    arm_motor.reset()
    log.info("reset: arm lowered, rotation sensor zeroed")


def release(arm_motor):
    """
    My Block #3: RELEASE
    Lower arm backward until rotation sensor reads <= 0 degrees.
    This lowers the grabber and opens the claws (gravity opens them last).
    Speed -50%, check rotation sensor each loop iteration.
    """
    log.info("release: lowering arm to rotation sensor = 0")
    arm_motor.on(SpeedPercent(-50))
    while arm_motor.position > 5:   # 5 degree tolerance
        sleep(0.01)
    arm_motor.off(brake=False)
    log.info("release: arm lowered")


# -------------------------------------------------------------
#  SEARCH ALGORITHM  (Valk My Block #4: Search, pages 46-50)
# -------------------------------------------------------------

def search(tank, ir_sensor, speaker):
    """
    My Block #4: SEARCH
    Makes one complete left turn (motor C = 1800 degrees),
    continuously reading beacon heading. Tracks the lowest
    non-zero absolute heading and the motor C position where
    it was recorded. Then turns right back to that position.
    Robot ends up facing the beacon.

    Variables (matching book exactly):
      Lowest   - best (lowest) absolute heading seen, init = 26
      Position - motor C degrees when Lowest was recorded, init = 0
      Reading  - current absolute heading value
    """
    log.info("search: starting 360 degree beacon scan")

    # Initialize variables (book Figure 18-12)
    lowest = 26    # any valid reading (1-25) will beat this
    position = 0   # motor C degrees at best detection

    # Reset motor C rotation sensor, then start turning LEFT
    # B+C tank: left=-100, right=+100 - spins left in place, speed 30
    tank.right_motor.reset()   # reset motor C (right motor) sensor to 0
    tank.on(SpeedPercent(-30), SpeedPercent(30))   # turn left

    # Scan loop - runs until motor C has turned 1800 degrees (- 360-)
    while True:
        motor_c_degrees = abs(tank.right_motor.position)

        if motor_c_degrees >= 1800:
            break

        # Read beacon heading (channel 1, beacon mode active on remote)
        try:
            heading = ir_sensor.heading(channel=1)   # -25 to +25
        except Exception as e:
            log.warning("search: beacon read error: %s", e)
            sleep(0.02)
            continue

        if heading is None:
            sleep(0.02)
            continue

        # reading = absolute value of heading
        reading = abs(heading)

        # Only process non-zero readings (0 = beacon behind robot)
        if reading != 0:
            if reading < lowest:
                lowest = reading
                position = motor_c_degrees
                log.info("search: new best - heading=%d at motor_c=%d", reading, position)
                speaker.beep()   # audio confirmation (book Figure 18-15)

        sleep(0.02)

    log.info("search: scan complete. Lowest=%d at Position=%d degrees", lowest, position)

    # Turn RIGHT until motor C rotation sensor is back at 'position'
    # Motor C was counting up as we turned left; now we turn right until it drops back
    tank.on(SpeedPercent(30), SpeedPercent(-30))   # turn right

    while abs(tank.right_motor.position) > position + 5:
        sleep(0.01)

    tank.off(brake=True)
    log.info("search: aligned to beacon direction")


# -------------------------------------------------------------
#  MAIN SNATCH3R CLASS
# -------------------------------------------------------------

class SNATCH3R:
    """
    Main SNATCH3R controller.

    Two modes (EV3 UP button to toggle):
      REMOTE     - drive with IR remote; beacon button grabs/releases
      AUTONOMOUS - full search-approach-grab-move-release cycle

    EV3 brick button CENTER = emergency stop.
    """

    def __init__(self):
        log.info("Initializing SNATCH3R")

        # Motors
        self.arm_motor   = MediumMotor(OUTPUT_A)
        self.left_motor  = LargeMotor(OUTPUT_B)
        self.right_motor = LargeMotor(OUTPUT_C)
        self.tank        = MoveTank(OUTPUT_B, OUTPUT_C)
        self.steering    = MoveSteering(OUTPUT_B, OUTPUT_C)

        # Sensors
        self.touch_sensor = TouchSensor(INPUT_1)
        self.ir_sensor    = InfraredSensor(INPUT_4)

        # EV3 peripherals
        self.speaker = Sound()
        self.screen  = Display()
        self.buttons = Button()
        self.speaker.set_volume(100)

        # State
        self.autonomous_mode = False
        self.shutdown_event  = Event()
        self.claw_raised     = False

        # EV3 brick button handlers
        self.buttons.on_up    = self._toggle_mode
        self.buttons.on_enter = self._stop

        # OS signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT,  self._signal_handler)

    # -- Startup ----------------------------------------------

    def initialize(self):
        """Run reset sequence and show startup screen."""
        self._show("SNATCH3R\nResetting...\n(claws must\nbe empty)")
        reset(self.arm_motor, self.touch_sensor)
        self.speaker.beep()
        self._show_mode()
        log.info("SNATCH3R ready")

    # -- Display helpers --------------------------------------

    def _show(self, text):
        self.screen.text_grid(text, clear_screen=True)
        self.screen.update()

    def _show_mode(self):
        mode = "AUTO" if self.autonomous_mode else "REMOTE"
        self._show("SNATCH3R\nMode: %s\nUP: toggle\nCTR: stop" % mode)

    # -- Button handlers --------------------------------------

    def _toggle_mode(self, state=None):
        if state is False:
            return
        self.autonomous_mode = not self.autonomous_mode
        log.info("Mode: %s", "AUTO" if self.autonomous_mode else "REMOTE")
        self._show_mode()

    def _stop(self, state=None):
        if state is False:
            return
        self.shutdown_event.set()

    def _signal_handler(self, sig, frame):
        log.info("Signal %s received", sig)
        self.shutdown_event.set()

    # -- Remote Control Mode ----------------------------------

    def _run_remote_mode(self):
        """
        IR remote channel 1 layout (from book Figure 18-9):
          Top-left     = Forward
          Bottom-left  = Backward (two bottom = backward)
          Top-right    = Right turn
          Bottom-right = Left turn  (book: left/right labels on remote)
          Beacon btn   = Grab (press) / Release (press again)
        Channel 4 any button = stop program
        """
        log.info("Remote mode active")
        self._show("REMOTE MODE\nCh1: drive\nBeacon: grab\nCh4: quit")

        ir = self.ir_sensor
        SPEED = 50

        ir.on_channel1_top_left     = self._make_drive(SPEED,  SPEED)
        ir.on_channel1_bottom_left  = self._make_drive(-SPEED, -SPEED)
        ir.on_channel1_top_right    = self._make_drive(SPEED,  -SPEED)
        ir.on_channel1_bottom_right = self._make_drive(-SPEED,  SPEED)
        ir.on_channel1_beacon       = self._remote_grab_release

        ir.on_channel4_top_left     = lambda s: self.shutdown_event.set() if s else None
        ir.on_channel4_top_right    = lambda s: self.shutdown_event.set() if s else None
        ir.on_channel4_bottom_left  = lambda s: self.shutdown_event.set() if s else None
        ir.on_channel4_bottom_right = lambda s: self.shutdown_event.set() if s else None

        while not self.shutdown_event.is_set() and not self.autonomous_mode:
            try:
                ir.process()
            except OSError as e:
                log.warning("remote: IR error: %s", e)
            sleep(0.01)

        # Clear handlers
        for attr in ['on_channel1_top_left','on_channel1_bottom_left',
                     'on_channel1_top_right','on_channel1_bottom_right',
                     'on_channel1_beacon',
                     'on_channel4_top_left','on_channel4_top_right',
                     'on_channel4_bottom_left','on_channel4_bottom_right']:
            setattr(ir, attr, None)

        self.tank.off(brake=False)

    def _make_drive(self, left, right):
        def handler(state):
            if state:
                self.tank.on(SpeedPercent(left), SpeedPercent(right))
            else:
                self.tank.off(brake=False)
        return handler

    def _remote_grab_release(self, state):
        if not state:
            return
        if not self.claw_raised:
            log.info("remote: grabbing")
            self._show("REMOTE\nGrabbing...")
            grab(self.arm_motor, self.touch_sensor)
            self.claw_raised = True
            self._show("REMOTE\nArm UP\nBeacon=release")
        else:
            log.info("remote: releasing")
            self._show("REMOTE\nReleasing...")
            release(self.arm_motor)
            self.claw_raised = False
            self._show("REMOTE\nArm DOWN\nBeacon=grab")

    # -- Autonomous Mode --------------------------------------

    def _run_autonomous_mode(self):
        """
        Full autonomous cycle from book pages 52-54:
          1. Reset
          2. Search + drive forward until proximity < 50
          3. Approach: drive forward with proportional steering until proximity < 1
          4. Drive forward 1 rotation to seat IR bug
          5. Grab
          6. Turn around (~2 rotations tank spin)
          7. Drive forward 2 rotations
          8. Release
        """
        log.info("Autonomous mode starting")
        self._show("AUTO MODE\nSearching...")

        # -- Step 1: Search until proximity < 50 -------------
        # (book Figure 18-19: loop Search + nudge forward until nearby)
        while not self.shutdown_event.is_set():
            search(self.tank, self.ir_sensor, self.speaker)
            if self.shutdown_event.is_set():
                return

            try:
                proximity = self.ir_sensor.proximity
            except Exception:
                proximity = 100

            log.info("auto: post-search proximity=%d", proximity)

            if proximity < 50:
                break

            # Nudge forward then search again
            self.tank.on_for_rotations(SpeedPercent(75), SpeedPercent(75), 4)

        # -- Step 2: Proportional steering approach -----------
        # (book Figure 18-20: steer = heading, drive until proximity < 1)
        log.info("auto: approaching beacon with proportional steering")
        self._show("AUTO MODE\nApproaching...")

        while not self.shutdown_event.is_set():
            try:
                heading  = self.ir_sensor.heading(channel=1)
                if heading is None:
                    heading = 0
                proximity = self.ir_sensor.proximity
            except Exception as e:
                log.warning("auto: sensor read error: %s", e)
                sleep(0.05)
                continue

            log.info("auto: heading=%d proximity=%d", heading, proximity)

            if proximity <= 1:
                self.tank.off(brake=True)
                break

            # Steering proportional to heading (book: "amount of steering
            # proportional to Beacon Heading")
            # MoveSteering: steering -100 (full left) to +100 (full right)
            # heading is -25 to +25, scale to steering range
            steering = heading * 4   # scale factor: 25 * 4 = 100 max
            steering = max(-100, min(100, steering))
            self.steering.on(steering, SpeedPercent(50))
            sleep(0.05)

        # -- Step 3: Drive forward 1 rotation to seat IR bug --
        log.info("auto: seating IR bug")
        self.tank.on_for_rotations(SpeedPercent(50), SpeedPercent(50), 1)

        # -- Step 4: Grab -------------------------------------
        log.info("auto: grabbing")
        self._show("AUTO MODE\nGrabbing!")
        grab(self.arm_motor, self.touch_sensor)
        sleep(0.3)

        # -- Step 5: Turn around ------------------------------
        # Book: turn around after grab (approx 180-)
        # Motor C needs ~1800 degrees for 360-, so ~900 for 180-
        log.info("auto: turning around")
        self._show("AUTO MODE\nTurning...")
        self.tank.on_for_degrees(SpeedPercent(100), SpeedPercent(-100), 900)

        # -- Step 6: Drive forward briefly --------------------
        log.info("auto: moving to new position")
        self.tank.on_for_rotations(SpeedPercent(50), SpeedPercent(50), 2)

        # -- Step 7: Release -----------------------------------
        log.info("auto: releasing")
        self._show("AUTO MODE\nReleasing...")
        release(self.arm_motor)

        log.info("auto: cycle complete")
        self._show("AUTO MODE\nDone!\nUP: remote\nCTR: stop")

        # After one cycle, drop back to remote mode so user can reposition
        self.autonomous_mode = False

    # -- Main loop ---------------------------------------------

    def main(self):
        self.initialize()

        while not self.shutdown_event.is_set():
            if self.autonomous_mode:
                self._run_autonomous_mode()
            else:
                self._run_remote_mode()

            self.buttons.process()

        # Shutdown
        log.info("Shutting down")
        self.tank.off(brake=False)
        self.arm_motor.off(brake=False)
        self._show("SNATCH3R\nStopped.")
        log.info("Shutdown complete")


# -------------------------------------------------------------
#  ENTRY POINT
# -------------------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)5s %(filename)s: %(message)s"
    )
    log = logging.getLogger(__name__)

    logging.addLevelName(logging.ERROR,
        "\033[91m  %s\033[0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING,
        "\033[91m%s\033[0m" % logging.getLevelName(logging.WARNING))

    log.info("Starting SNATCH3R")
    robot = SNATCH3R()
    robot.main()
    log.info("Exiting SNATCH3R")