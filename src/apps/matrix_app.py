import utime
import machine
import math

from neopixel import NeoPixel

from src.apps.app import App
from constants import (COLOR_BLACK, COLOR_ORANGE, COLOR_RED, COLOR_YELLOW, EXPLOSION_EFFECT, MATRIX_DEFAULT_BRIGHTNESS, MATRIX_DIGIT_PATTERNS,
                       MATRIX_HEIGHT, MATRIX_NUM_PIXELS, MATRIX_PIN_NUM, MATRIX_WIDTH, NOTES, OLED_WIDTH)


class MatrixEffectsApp(App):  # Functional sounds, menu sounds handled by base

    PLASMA_SOUND_FREQ = NOTES['C3']

    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.menu_items = ["9-0 Counter", "Plasma (10s)", "Back"]
        self.current_selection = 0
        self.matrix = None
        try:
            self.matrix = NeoPixel(machine.Pin(MATRIX_PIN_NUM), MATRIX_NUM_PIXELS)
            self._clear_matrix()
        except Exception as e:
            print(f"Error initializing LED Matrix: {e}")
            self.display.show_message(["Matrix Error!", "Check Pin/Lib"], title="ERROR", duration_s=3)

    def _neo_set_grb(self, index, r, g, b):
        if self.matrix:
            br = int(r*MATRIX_DEFAULT_BRIGHTNESS)
            bg = int(g*MATRIX_DEFAULT_BRIGHTNESS)
            bb = int(b*MATRIX_DEFAULT_BRIGHTNESS)
            self.matrix[index] = (max(0, min(255, bg)), max(0, min(255, br)), max(0, min(255, bb)))

    def _xy_to_neo(self, x, y): return y*MATRIX_WIDTH + x if 0 <= x < MATRIX_WIDTH and 0 <= y < MATRIX_HEIGHT else -1

    def _clear_matrix(self):
        if self.matrix:
            for i in range(MATRIX_NUM_PIXELS):
                self._neo_set_grb(i, 0, 0, 0)
            self.matrix.write()

    def _draw_digit(self, digit_val, color_rgb):
        if not self.matrix:
            return
        for i in range(MATRIX_NUM_PIXELS):
            self._neo_set_grb(i, *COLOR_BLACK)
        pattern = MATRIX_DIGIT_PATTERNS.get(digit_val)
        if pattern:
            for y, row in enumerate(pattern):
                for x, pixel_on in enumerate(row):
                    if pixel_on:
                        idx = self._xy_to_neo(x, y)
                        if idx != -1:
                            self._neo_set_grb(idx, *color_rgb)
        self.matrix.write()

    def _run_countdown(self):
        if not self.matrix:
            self.display.show_message("Matrix N/A", title="Error", duration_s=2)
            return
        self.display.show_message("Countdown!", title="Matrix FX", duration_s=1, clear_after=True)
        for i in range(9, -1, -1):
            self.display.clear()
            self.display.text(f"Countdown: {i}", 20, 25)
            self.display.show()
            self._draw_digit(i, COLOR_RED)
            self.buzzer.play_tone(NOTES['C5'], 150, duty_u16=16384)  # Functional sound
            utime.sleep_ms(850)
        self.buzzer._deinit_pwm()
        self._clear_matrix()
        self.display.clear()
        self.display.text("BOOM!", (OLED_WIDTH-5*8)//2, 25)
        self.display.show()
        flash_colors = [COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_BLACK]
        for _ in range(3):
            for color_rgb in flash_colors:
                if self.matrix:
                    for k in range(MATRIX_NUM_PIXELS):
                        self._neo_set_grb(k, *color_rgb)
                    self.matrix.write()
                utime.sleep_ms(100 if color_rgb != COLOR_BLACK else 70)
        self.buzzer.play_song(EXPLOSION_EFFECT)
        self._clear_matrix()
        utime.sleep(1)
        self.display.show_message("Press OK", title="Effect End", duration_s=0, clear_after=False)  # No auto clear
        start_wait_time = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), start_wait_time) < 5000:
            self.buttons['ok'].update()
            if self.buttons['ok'].is_pressed():
                if App._menu_buzzer_enabled and self.buzzer:
                    self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                break
            utime.sleep_ms(20)
        self._clear_matrix()

    def _run_plasma(self):
        if not self.matrix:
            self.display.show_message("Matrix N/A", title="Error", duration_s=2)
            return
        self.display.show_message("Plasma!", title="Matrix FX", duration_s=1.5, clear_after=True)
        self.buzzer.start_tone(self.PLASMA_SOUND_FREQ, duty_u16=8000)  # Functional sound
        start_ms = utime.ticks_ms()
        duration_ms = 10000
        time_val = 0.0
        sx, sy, sd, sp = 0.9, 0.9, 0.7, 0.15
        while utime.ticks_diff(utime.ticks_ms(), start_ms) < duration_ms:
            for y in range(MATRIX_HEIGHT):
                for x in range(MATRIX_WIDTH):
                    v = math.sin(x*sx+time_val) + math.sin(y*sy+time_val) + math.sin((x+y)*sd+time_val)
                    r = int((math.sin(v*math.pi)+1)*127.5)
                    g = int((math.sin(v*math.pi+2*math.pi/3)+1)*127.5)
                    b = int((math.sin(v*math.pi+4*math.pi/3)+1)*127.5)
                    idx = self._xy_to_neo(x, y)
                    if idx != -1:
                        self._neo_set_grb(idx, r, g, b)
            self.matrix.write()
            time_val += sp
            utime.sleep_ms(40)
            self.buttons['ok'].update()
            if self.buttons['ok'].is_pressed():
                if App._menu_buzzer_enabled and self.buzzer:
                    self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)  # OK to exit plasma
                break
        self.buzzer.stop_tone()
        self._clear_matrix()
        self.display.show_message(["Plasma End", "Press OK"], title="Effect End", duration_s=0, clear_after=False)  # No auto clear
        start_wait_time = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), start_wait_time) < 5000:
            self.buttons['ok'].update()
            if self.buttons['ok'].is_pressed():
                if App._menu_buzzer_enabled and self.buzzer:
                    self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                break
            utime.sleep_ms(20)
        self._clear_matrix()

    def run(self):
        self._active = True
        if not self.matrix and self.menu_items[0] != "Back":
            self.menu_items = ["Matrix N/A", "Back"]
            self.current_selection = 0
        while self._active:
            for btn_obj in self.buttons.values():
                btn_obj.update()
            self.display.draw_menu(self.menu_items, self.current_selection, title="Matrix Effects")
            new_selection, ok_pressed = self._handle_input_for_menu(len(self.menu_items), self.current_selection)
            self.current_selection = new_selection
            if ok_pressed:
                selected_title = self.menu_items[self.current_selection]
                if selected_title == "Back":
                    self.stop()
                elif selected_title == "9-0 Counter":
                    self._run_countdown()
                elif selected_title == "Plasma (10s)":
                    self._run_plasma()
                elif selected_title == "Matrix N/A":
                    pass
            utime.sleep_ms(50)

    def stop(self):
        super().stop()
        self._clear_matrix()
