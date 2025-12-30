#!/usr/bin/env python3

"""
Implementation of R3PTAR
"""

import logging
import signal
import sys
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
        tick = 0

        while True:

            if self.shutdown_event.is_set():
                log.info('%s: shutdown_event is set' % self)
                break

            #log.info("proximity: %s" % self.parent.remote.proximity)
            if self.parent.remote.proximity < STRIKE_DISTANCE:
                log.info('%s: proximity < %s, striking' % (self, STRIKE_DISTANCE))
                self.parent.screen.text_grid('Striking!', clear_screen=True)
                self.parent.screen.update()
                self.parent.speaker.play_file('/home/robot/R3PTAR/snake-hiss.wav', Sound.PLAY_NO_WAIT_FOR_COMPLETE)
                self.parent.strike_motor.on_for_seconds(speed=STRIKE_SPEED_PCT, seconds=0.2)
                self.parent.strike_motor.on_for_seconds(speed=(STRIKE_SPEED_PCT * -1), seconds=0.2)

            self.parent.remote.process()
            tick += 1
            if tick % 200 == 0:
                log.info('%s: proximity=%s' % (self, self.parent.remote.proximity))
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
