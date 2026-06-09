#!/usr/bin/env micropython

import logging
from time import sleep

from ev3dev2.motor import MediumMotor, LargeMotor, SpeedPercent, MoveSteering, OUTPUT_A, OUTPUT_B, OUTPUT_C
from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3, INPUT_4
from ev3dev2.sensor.lego import TouchSensor, ColorSensor, InfraredSensor
from ev3dev2.port import LegoPort
from ev3dev2.sound import Sound
from ev3dev2.button import Button

# Configure brick variables
medium_motor = MediumMotor(OUTPUT_A)
right_motor = LargeMotor(OUTPUT_B)
left_motor = LargeMotor(OUTPUT_C)
touch_sensor = TouchSensor(INPUT_2)
color_sensor = ColorSensor(INPUT_3)
infrared_sensor = InfraredSensor(INPUT_4)
steering_drive = MoveSteering(OUTPUT_B, OUTPUT_C)
sound = Sound()
button = Button()

# Logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)5s: %(message)s')
log = logging.getLogger(__name__)
log.info("Starting")

# Play startup sound
sound.play_file("/home/robot/sounds/Confirm.wav")

# Define functions


def grab(channel=1):
    medium_motor.duty_cycle_sp = 50 + (channel - 1) * 25
    medium_motor.run_direct()
    touch_sensor.wait_for_pressed()
    medium_motor.stop()


def reset():
    grab()
    medium_motor.on_for_rotations(-50, 14.2)
    medium_motor.reset()


def release(channel=1):
    # log.info("starting release")
    medium_motor.duty_cycle_sp = -50 + (channel - 1) * 25
    medium_motor.run_direct()
    min_degrees = medium_motor.degrees
    iterations_at_min = 0
    while iterations_at_min < 10:
        # log.info("degrees: {:6.2f}".format(medium_motor.degrees))
        degrees = medium_motor.degrees
        if degrees < min_degrees:
            min_degrees = degrees
            iterations_at_min = 0
        else:
            iterations_at_min += 1

    medium_motor.stop()
    # log.info("finished release")


# Start program

buttons_pressed_4 = ''

while len(buttons_pressed_4) == 0:

    # log.info("buttons pressed on channel 1: " + str(buttons_pressed_1))
    # log.info("buttons pressed on channel 2: " + str(buttons_pressed_2))
    # log.info("buttons pressed on channel 3: " + str(buttons_pressed_3))
    # log.info("buttons pressed on channel 4: " + str(buttons_pressed_4))

    buttons_pressed_1 = infrared_sensor.buttons_pressed(channel=1)
    buttons_pressed_2 = infrared_sensor.buttons_pressed(channel=2)
    buttons_pressed_3 = infrared_sensor.buttons_pressed(channel=3)
    buttons_pressed_4 = infrared_sensor.buttons_pressed(channel=4)

    if len(buttons_pressed_1) == 0 and len(buttons_pressed_2) == 0 and len(buttons_pressed_3) == 0:
        steering_drive.off()
    if buttons_pressed_1 == ['top_left', 'top_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(50))
    if buttons_pressed_1 == ['top_left']:
        steering_drive.on(steering=-100, speed=SpeedPercent(50))
    if buttons_pressed_1 == ['top_right']:
        steering_drive.on(steering=100, speed=SpeedPercent(50))
    if buttons_pressed_1 == ['bottom_left', 'bottom_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(-50))
    if buttons_pressed_1 == ['bottom_left']:
        steering_drive.off()
        grab()
    if buttons_pressed_1 == ['bottom_right']:
        steering_drive.off()
        release()

    if buttons_pressed_2 == ['top_left', 'top_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(75))
    if buttons_pressed_2 == ['top_left']:
        steering_drive.on(steering=-100, speed=SpeedPercent(75))
    if buttons_pressed_2 == ['top_right']:
        steering_drive.on(steering=100, speed=SpeedPercent(75))
    if buttons_pressed_2 == ['bottom_left', 'bottom_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(-75))
    if buttons_pressed_2 == ['bottom_left']:
        steering_drive.off()
        grab()
    if buttons_pressed_2 == ['bottom_right']:
        steering_drive.off()
        release()

    if buttons_pressed_3 == ['top_left', 'top_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(100))
    if buttons_pressed_3 == ['top_left']:
        steering_drive.on(steering=-100, speed=SpeedPercent(100))
    if buttons_pressed_3 == ['top_right']:
        steering_drive.on(steering=100, speed=SpeedPercent(100))
    if buttons_pressed_3 == ['bottom_left', 'bottom_right']:
        steering_drive.on(steering=0, speed=SpeedPercent(-100))
    if buttons_pressed_3 == ['bottom_left']:
        steering_drive.off()
        grab()
    if buttons_pressed_3 == ['bottom_right']:
        steering_drive.off()
        release()