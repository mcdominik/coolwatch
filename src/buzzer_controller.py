import machine
from src.constants import NOTES
import utime


class BuzzerController:
    """Handles passive buzzer basic sounds"""

    def __init__(self, pin_num, button_sounds):
        self.pwm_pin_num = pin_num
        self.button_sounds = button_sounds
        self.buzzer = None

    # TODO CLEAN INITIALIZATION AND NAMING
    def _init_pwm(self):
        if self.buzzer is None:
            pin_obj = machine.Pin(self.pwm_pin_num)
            self.buzzer = machine.PWM(pin_obj)

    def _deinit_pwm(self):
        if self.buzzer:
            self.buzzer.duty_u16(0)
            self.buzzer.deinit()
            self.buzzer = None

    def play_tone(self, freq, duration_ms, duty_u16=32768):
        if not self.button_sounds:
            return
        if freq <= 0:
            self.rest(duration_ms)
            return
        self._init_pwm()
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(duty_u16)
        utime.sleep_ms(duration_ms)
        self.buzzer.duty_u16(0)

    def play_flip_sound(self):
        self.play_tone(NOTES['C5'], 50)
        self.play_tone(NOTES['E5'], 50)
        self.play_tone(NOTES['G5'], 80)
        # TODO incpect deinit
        # self._deinit_pwm()

    def play_ok_sound(self):
        self.play_tone(NOTES['E5'], 50, duty_u16=10000)

    def play_exit_sound(self):
        self.play_tone(NOTES['C5'], 30, duty_u16=8000)

    def start_tone(self, freq, duty_u16=32768):
        if freq <= 0:
            if self.buzzer:
                self.buzzer.duty_u16(0)
            return
        self._init_pwm()
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(duty_u16)

    def stop_tone(self):
        if self.buzzer:
            self.buzzer.duty_u16(0)
        self._deinit_pwm()

    def rest(self, duration_ms):
        if self.buzzer:
            self.buzzer.duty_u16(0)
        utime.sleep_ms(duration_ms)

    def play_song(self, song_data, display_manager=None):
        for i, item in enumerate(song_data):
            note_val, duration = item[0], item[1]
            delay_after = item[2] if len(item) > 2 else 50
            freq = NOTES.get(note_val, 0) if isinstance(note_val, str) else note_val
            if display_manager:
                display_manager.clear()
                display_manager.text("Playing...", 20, 20)
                display_manager.text(f"Note {i+1}/{len(song_data)}", 20, 30)
                display_manager.show()
            self.play_tone(freq, duration)
            if delay_after > 0 and freq > 0:
                utime.sleep_ms(delay_after)
        self._deinit_pwm()
