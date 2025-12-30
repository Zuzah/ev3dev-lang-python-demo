#!/usr/bin/env python3

"""
Implementation of R3PTAR
"""

import logging
import signal
import sys
import subprocess
import os
import time
from ev3dev2.motor import OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D, MediumMotor, LargeMotor
from ev3dev2.sensor.lego import InfraredSensor
from ev3dev2.display import Display
from ev3dev2.sound import Sound
from threading import Thread, Event
from time import sleep

log = logging.getLogger(__name__)


class MonitorRemoteControl(Thread):
    """
    A thread to monitor R3PTAR's InfraredSensor and process signals
    from the remote control
    """

    def __init__(self, parent):
        Thread.__init__(self)
        self.parent = parent
        self.shutdown_event = Event()

    def __str__(self):
        return "MonitorRemoteControl"

    def run(self):
        STRIKE_SPEED_PCT = 40
        STRIKE_DISTANCE = 30
        STRIKE_FORWARD_SEC = 0.15
        STRIKE_BACK_SEC = 0.15
        STRIKE_COOLDOWN = 0.7
        RATTLE_INTERVAL = 8.0
        SOUND_COOLDOWN = 0.8
        HISS_SOUND = '/home/robot/R3PTAR/snake-hiss.wav'
        RATTLE_SOUND = '/home/robot/R3PTAR/rattle-snake.wav'
        last_sound_time = 0.0
        last_rattle_time = 0.0
        next_strike_time = 0.0
        last_log_time = 0.0

        while True:

            if self.shutdown_event.is_set():
                log.info('%s: shutdown_event is set' % self)
                break

            now = time.monotonic()
            proximity = self.parent.remote.proximity

            if now - last_log_time >= 1.0:
                log.info('%s: proximity=%s', self, proximity)
                last_log_time = now

            if proximity < STRIKE_DISTANCE and now >= next_strike_time:
                log.info('%s: proximity < %s, striking', self, STRIKE_DISTANCE)
                self.parent.screen.text_grid('Striking!', clear_screen=True)
                self.parent.screen.update()
                if now - last_sound_time >= SOUND_COOLDOWN and os.path.exists(HISS_SOUND):
                    log.info('%s: playing hiss sound', self)
                    subprocess.Popen(['aplay', '-q', HISS_SOUND])
                    last_sound_time = now
                elif not os.path.exists(HISS_SOUND):
                    log.warning('%s: sound file missing: %s', self, HISS_SOUND)

                self.parent.strike_motor.on_for_seconds(speed=STRIKE_SPEED_PCT, seconds=STRIKE_FORWARD_SEC)
                self.parent.strike_motor.on_for_seconds(speed=(STRIKE_SPEED_PCT * -1), seconds=STRIKE_BACK_SEC)
                next_strike_time = time.monotonic() + STRIKE_COOLDOWN
                last_rattle_time = time.monotonic()
            elif now - last_rattle_time >= RATTLE_INTERVAL:
                if now - last_sound_time >= SOUND_COOLDOWN and os.path.exists(RATTLE_SOUND):
                    log.info('%s: playing rattle sound', self)
                    subprocess.Popen(['aplay', '-q', RATTLE_SOUND])
                    last_sound_time = now
                    last_rattle_time = now
                elif not os.path.exists(RATTLE_SOUND):
                    log.warning('%s: sound file missing: %s', self, RATTLE_SOUND)
                    last_rattle_time = now

            sleep(0.005)


class R3PTAR(object):

    def __init__(self,
                 drive_motor_port=OUTPUT_B,
                 strike_motor_port=OUTPUT_D,
                 steer_motor_port=OUTPUT_A,
                 drive_speed_pct=60):

        self.drive_motor = LargeMotor(drive_motor_port)
        self.strike_motor = LargeMotor(strike_motor_port)
        self.steer_motor = MediumMotor(steer_motor_port)
        self.speaker = Sound()
        self.speaker.set_volume(100)
        self.screen = Display()
        STEER_SPEED_PCT = 30

        self.remote = InfraredSensor()
        log.info('IR sensor address=%s' % self.remote.address)
        self.screen.text_grid('R3PTAR ready', clear_screen=True)
        self.screen.update()
        self.remote.on_channel1_top_left = self.make_move(self.drive_motor, drive_speed_pct)
        self.remote.on_channel1_bottom_left = self.make_move(self.drive_motor, drive_speed_pct * -1)
        self.remote.on_channel1_top_right = self.make_move(self.steer_motor, STEER_SPEED_PCT)
        self.remote.on_channel1_bottom_right = self.make_move(self.steer_motor, STEER_SPEED_PCT * -1)

        self.shutdown_event = Event()
        self.mrc = MonitorRemoteControl(self)

        # Register our signal_term_handler() to be called if the user sends
        # a 'kill' to this process or does a Ctrl-C from the command line
        signal.signal(signal.SIGTERM, self.signal_term_handler)
        signal.signal(signal.SIGINT, self.signal_int_handler)

    def make_move(self, motor, speed):
        def move(state):
            if state:
                log.info('remote: motor=%s speed=%s' % (motor.address, speed))
                motor.on(speed)
            else:
                motor.stop()
        return move

    def shutdown_robot(self):

        if self.shutdown_event.is_set():
            return

        self.shutdown_event.set()
        log.info('shutting down')
        self.mrc.shutdown_event.set()

        self.remote.on_channel1_top_left = None
        self.remote.on_channel1_bottom_left = None
        self.remote.on_channel1_top_right = None
        self.remote.on_channel1_bottom_right = None

        self.drive_motor.off(brake=False)
        self.strike_motor.off(brake=False)
        self.steer_motor.off(brake=False)

        self.mrc.join()

    def signal_term_handler(self, signal, frame):
        log.info('Caught SIGTERM')
        self.shutdown_robot()

    def signal_int_handler(self, signal, frame):
        log.info('Caught SIGINT')
        self.shutdown_robot()

    def main(self):
        self.mrc.start()
        self.shutdown_event.wait()


if __name__ == '__main__':

    # Change level to logging.DEBUG for more details
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)5s %(filename)s: %(message)s")
    log = logging.getLogger(__name__)

    # Color the errors and warnings in red
    logging.addLevelName(logging.ERROR, "\033[91m  %s\033[0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING, "\033[91m%s\033[0m" % logging.getLevelName(logging.WARNING))

    log.info("Starting R3PTAR")
    snake = R3PTAR()
    snake.main()
    log.info("Exiting R3PTAR")
