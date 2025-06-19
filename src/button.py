import machine
from src.constants import DEBOUNCE_MS
import utime


class Button:

    def __init__(self, pin_id, pull=machine.Pin.PULL_UP):
        self.pin = machine.Pin(pin_id, machine.Pin.IN, pull)
        self.debounce_ms = DEBOUNCE_MS
        self.last_press_time = 0
        self.initial_state = self.pin.value()
        self.last_state = self.initial_state
        self._pressed_event = False

    def update(self):
        self._pressed_event = False
        current_state = self.pin.value()
        now = utime.ticks_ms()
        if current_state != self.last_state:
            if utime.ticks_diff(now, self.last_press_time) > self.debounce_ms:
                if self.last_state == 1 and current_state == 0:
                    self._pressed_event = True
                self.last_press_time = now
        self.last_state = current_state

    def is_pressed(self):
        return self._pressed_event

    def value(self):
        return self.pin.value()
