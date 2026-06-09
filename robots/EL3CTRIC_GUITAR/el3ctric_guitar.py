#!/usr/bin/env python3


from ev3dev2.motor import MediumMotor, OUTPUT_D
from ev3dev2.sensor import INPUT_1, INPUT_4
from ev3dev2.sensor.lego import TouchSensor, InfraredSensor
from ev3dev2.led import Leds
from ev3dev2.sound import Sound
import os
import subprocess
import time
from random import randint

from time import sleep
from random import randint


class El3ctricGuitar:
    NOTES = [1318, 1174, 987, 880, 783, 659, 587, 493, 440, 392, 329, 293]
    N_NOTES = len(NOTES)

    def __init__(
            self, lever_motor_port: str = OUTPUT_D,
            touch_sensor_port: str = INPUT_1, ir_sensor_port: str = INPUT_4):
        self.lever_motor = MediumMotor(address=lever_motor_port)

        self.touch_sensor = TouchSensor(address=touch_sensor_port)

        self.ir_sensor = InfraredSensor(address=ir_sensor_port)
        
        self.leds = Leds()

        self.speaker = Sound()
        self.sounds_root = '/home/robot/EL3CTRIC_GUITAR/sounds'
        self.sound_set = 'brutal_legends'
        self.sound_files = self.load_sound_set()
        self.last_play_time = 0.0
        self.play_cooldown = 0.25
        self.last_index = None

    def start_up(self):
        self.leds.animate_flash(
            color='ORANGE',
            groups=('LEFT', 'RIGHT'),
            sleeptime=0.5,
            duration=3,
            block=True)

        self.lever_motor.on_for_seconds(
            speed=5,
            seconds=1,
            brake=False,
            block=True)

        self.lever_motor.on_for_degrees(
            speed=-5,
            degrees=30,
            brake=True,
            block=True)

        sleep(0.1)

        self.lever_motor.reset()

    def load_sound_set(self):
        folder = os.path.join(self.sounds_root, self.sound_set)
        if not os.path.isdir(folder):
            return []
        files = []
        for entry in sorted(os.listdir(folder)):
            if entry.lower().endswith('.wav'):
                files.append(os.path.join(folder, entry))
        return files

    def pick_sample(self, index):
        if not self.sound_files:
            return None
        index = max(0, min(index, len(self.sound_files) - 1))
        jitter = randint(-1, 1)
        choice = max(0, min(index + jitter, len(self.sound_files) - 1))
        if self.last_index is not None and choice == self.last_index:
            choice = max(0, min(index + 1, len(self.sound_files) - 1))
        self.last_index = choice
        return self.sound_files[choice]

    def play_sample(self, path):
        now = time.monotonic()
        if now - self.last_play_time < self.play_cooldown:
            return
        self.last_play_time = now
        subprocess.Popen(['aplay', '-q', path])

    def play_music(self):
        if self.touch_sensor.is_released:
            raw = sum(self.ir_sensor.proximity for _ in range(4)) / 4
            if self.sound_files:
                idx = int((raw / 100.0) * len(self.sound_files))
                sample = self.pick_sample(idx)
                if sample:
                    self.play_sample(sample)
            else:
                self.speaker.tone(
                    self.NOTES[min(round(raw / 5), self.N_NOTES - 1)]
                    - 11 * self.lever_motor.position,
                    100,
                    play_type=Sound.PLAY_WAIT_FOR_COMPLETE)

    def main(self):
        self.start_up()
        while True:
            self.play_music()


if __name__ == '__main__':
    EL3CTRIC_GUITAR = El3ctricGuitar()
    EL3CTRIC_GUITAR.main()
