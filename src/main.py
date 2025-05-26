import machine
import utime
import framebuf
import random
import math

from neopixel import NeoPixel

from src.ssd1306 import SSD1306_I2C
from src.constants import (
    OLED_SDA_PIN_NUM,
    OLED_SCL_PIN_NUM,
    OLED_WIDTH,
    OLED_HEIGHT,
    OLED_I2C_ADDR,
    OLED_I2C_ID,
    BUZZER_PIN_NUM,
    NOTES,
    BUTTON_UP_PIN_NUM,
    BUTTON_DOWN_PIN_NUM,
    BUTTON_OK_PIN_NUM,
    DEBOUNCE_MS,
    TEMP_SENSOR_ADC_CHANNEL,
    TEMPERATURE_OFFSET,
    MATRIX_PIN_NUM,
    MATRIX_NUM_PIXELS,
    MATRIX_WIDTH,
    MATRIX_HEIGHT,
    MATRIX_DEFAULT_BRIGHTNESS,
    MATRIX_DIGIT_PATTERNS,
    COLOR_RED,
    COLOR_BLACK,
    COLOR_ORANGE,
    COLOR_YELLOW,
    SLEEP_SWITCH_PIN_NUM,
    IMPERIAL_MARCH_MELODY,
    PIRATES_MELODY,
    BIRTHDAY_MELODY,
    EXPLOSION_EFFECT
)


class SleepManager:
    """Handles RP2040-Matrix sleep mode functionality"""

    def __init__(self, sleep_pin_num):
        self.sleep_pin = machine.Pin(sleep_pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
        self.is_sleeping = False

    def should_sleep(self):
        """Check if device should enter sleep mode (pin LOW = switch closed = sleep)"""
        return self.sleep_pin.value() == 0

    def enter_sleep_mode(self, display_manager, buzzer_control):
        """Enter sleep mode improving battery life"""
        if self.is_sleeping:
            return

        print("Entering sleep mode...")
        display_manager.clear()
        display_manager.text("Sleep mode..", 20, 25)
        display_manager.show()
        utime.sleep_ms(500)

        self.is_sleeping = True
        display_manager.oled.poweroff()

        if buzzer_control:
            buzzer_control.stop_tone()

    def exit_sleep_mode(self, display_manager):
        """Exit sleep mode"""
        if not self.is_sleeping:
            return

        print("Exiting sleep mode..")
        self.is_sleeping = False
        display_manager.oled.poweron()
        display_manager.clear()
        display_manager.text("Waking up...", 20, 25)
        display_manager.show()
        utime.sleep_ms(500)


class Button:

    def __init__(self, pin_id, pull=machine.Pin.PULL_UP, name="Button"):
        self.pin = machine.Pin(pin_id, machine.Pin.IN, pull)
        self.debounce_ms = DEBOUNCE_MS
        self.last_press_time = 0
        self.initial_state = self.pin.value()
        self.last_state = self.initial_state
        self._pressed_event = False
        self.name = name

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


class Buzzer:
    """Handles passive buzzer basic sounds"""

    def __init__(self, pin_num, enable):
        self.pwm_pin_num = pin_num
        self.enable = enable
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
        if not self.enable:
            return
        # if freq <= 0:
        #     self.rest(duration_ms)
        #     return
        self._init_pwm()
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(duty_u16)
        utime.sleep_ms(duration_ms)
        self.buzzer.duty_u16(0)

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


class DisplayManager:
    """Handles display functionality for monochromatic OLED"""

    def __init__(self, oled):
        self.oled = oled
        self.text_height = 8
        self.line_padding = 2
        self._char_fbuf_data = bytearray(self.text_height * (self.text_height // 8))
        self._char_fbuf = framebuf.FrameBuffer(self._char_fbuf_data, self.text_height, self.text_height, framebuf.MONO_HLSB)

    def clear(self):
        self.oled.fill(0)

    def text(self, s, x, y, color=1):
        self.oled.text(s, x, y, color)

    def show(self):
        self.oled.show()

    def text_scaled(self, text_string, x_start, y_start, scale, color=1):
        char_width_scaled = self.text_height * scale
        current_x = x_start
        for char_val in text_string:
            self._char_fbuf.fill(0)
            self._char_fbuf.text(char_val, 0, 0, color)
            for y_char_pix in range(self.text_height):
                for x_char_pix in range(self.text_height):
                    if self._char_fbuf.pixel(x_char_pix, y_char_pix):
                        self.oled.fill_rect(current_x + x_char_pix * scale,
                                            y_start + y_char_pix * scale,
                                            scale, scale, color)
            current_x += char_width_scaled

    def draw_menu(self, menu_item_titles, selected_index, title="", max_visible_items=5):
        self.clear()
        current_y = 0
        if title:
            title_x = (self.oled.width - len(title) * self.text_height) // 2
            self.text(title, title_x if title_x > 0 else 0, current_y)
            current_y += self.text_height + self.line_padding * 2

        num_items = len(menu_item_titles)
        window_start = 0
        if num_items > max_visible_items:
            if selected_index >= window_start + max_visible_items:
                window_start = selected_index - max_visible_items + 1
            elif selected_index < window_start:
                window_start = selected_index
        if window_start < 0:
            window_start = 0
        if num_items > max_visible_items and window_start > num_items - max_visible_items:
            window_start = num_items - max_visible_items
        window_end = min(num_items, window_start + max_visible_items)

        for i in range(window_start, window_end):
            item_title = menu_item_titles[i]
            prefix = "> " if i == selected_index else "  "
            self.text(prefix + item_title, 5, current_y)
            current_y += self.text_height + self.line_padding
        self.show()

    def show_message(self, message_lines, title="", duration_s=0, clear_after=True):
        self.clear()
        current_y = 0
        if title:
            title_x = (self.oled.width - len(title) * self.text_height) // 2
            self.text(title, title_x if title_x > 0 else 0, current_y)
            current_y += self.text_height + self.line_padding

        if isinstance(message_lines, str):
            message_lines = [message_lines]

        for line in message_lines:
            max_chars_line = self.oled.width // self.text_height
            if len(line) > max_chars_line:
                words = line.split(' ')
                current_line_text = ""
                for word_idx, word in enumerate(words):
                    if len(current_line_text) + len(word) + (1 if current_line_text else 0) <= max_chars_line:
                        if current_line_text:
                            current_line_text += " "
                        current_line_text += word
                    else:
                        self.text(current_line_text, 0, current_y)
                        current_y += self.text_height + self.line_padding
                        current_line_text = word
                    if word_idx == len(words) - 1 and current_line_text:
                        self.text(current_line_text, 0, current_y)
                        current_y += self.text_height + self.line_padding
            else:
                self.text(line, 0, current_y)
                current_y += self.text_height + self.line_padding
        self.show()
        if duration_s > 0:
            utime.sleep(duration_s)
            if clear_after:
                self.clear()
                self.show()


class App:
    _menu_buzzer_enabled = False

    def __init__(self, display_manager, buttons, buzzer_control):
        self.display = display_manager
        self.buttons = buttons
        self.buzzer = buzzer_control
        self._active = True

    def run(self):
        raise NotImplementedError

    def stop(self):
        self._active = False
        if self.buzzer:
            self.buzzer.stop_tone()  # Stop any continuous tones from the app

    def _handle_input_for_menu(self, menu_items_count, current_selection):
        if self.buttons['up'].is_pressed():
            current_selection = (current_selection - 1 + menu_items_count) % menu_items_count
            if App._menu_buzzer_enabled:
                self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
        elif self.buttons['down'].is_pressed():
            current_selection = (current_selection + 1) % menu_items_count
            if App._menu_buzzer_enabled:
                self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
        elif self.buttons['ok'].is_pressed():
            if App._menu_buzzer_enabled:
                self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
            return current_selection, True
        return current_selection, False


class SettingsApp(App):
    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.menu_items = []
        self.current_selection = 0
        self._update_menu_text()  # Initial setup of menu text

    def _update_menu_text(self):
        sound_status = "ON" if App._menu_buzzer_enabled else "OFF"
        self.menu_items = [f"Sounds: {sound_status}", "Back"]

    def run(self):
        self._active = True
        self.current_selection = 0  # Reset selection when app starts
        self._update_menu_text()   # Ensure menu text is current

        while self._active:
            for btn_obj in self.buttons.values():
                btn_obj.update()

            self._update_menu_text()  # Keep text updated if it could change (though it only changes on OK press here)
            self.display.draw_menu(self.menu_items, self.current_selection, title="Settings")

            # Use a local version of _handle_input_for_menu or manage sounds carefully
            # For simplicity, we'll rely on the base _handle_input_for_menu for navigation sounds (if enabled)
            # and add a specific sound for the toggle action.
            new_selection, ok_pressed = self._handle_input_for_menu(len(self.menu_items), self.current_selection)
            self.current_selection = new_selection

            if ok_pressed:
                selected_title = self.menu_items[self.current_selection]
                if selected_title.startswith("Sounds:"):
                    App._menu_buzzer_enabled = not App._menu_buzzer_enabled
                    # Play a distinct confirmation sound that is NOT subject to the setting itself
                    if self.buzzer:
                        self.buzzer.play_tone(NOTES['A4'] if App._menu_buzzer_enabled else NOTES['G4'], 70, duty_u16=10000)
                    self._update_menu_text()  # Update the menu item text immediately
                elif selected_title == "Back":
                    self.stop()

            utime.sleep_ms(50)


class MusicApp(App):

    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.songs = [
            {"title": "Star Wars", "data": IMPERIAL_MARCH_MELODY},
            {"title": "Pirates", "data": PIRATES_MELODY},
            {"title": "Birthday", "data": BIRTHDAY_MELODY},
        ]
        self.menu_items = [song["title"] for song in self.songs] + ["Back"]
        self.current_selection = 0

    def run(self):
        self._active = True
        while self._active:
            for btn_obj in self.buttons.values():
                btn_obj.update()
            self.display.draw_menu(self.menu_items, self.current_selection, title="Music Menu")
            new_selection, ok_pressed = self._handle_input_for_menu(len(self.menu_items), self.current_selection)
            self.current_selection = new_selection
            if ok_pressed:
                selected_item_title = self.menu_items[self.current_selection]
                if selected_item_title == "Back":
                    self.stop()
                else:
                    song_to_play = next((s for s in self.songs if s["title"] == selected_item_title), None)
                    if song_to_play:
                        self.display.show_message(f"Playing: {song_to_play['title']}", title="Music", duration_s=0.1, clear_after=False)
                        self.buzzer.play_song(song_to_play["data"], self.display)
                        self.display.show_message(["Song finished!", "Press OK."], title="Music")
                        start_wait_time = utime.ticks_ms()
                        while utime.ticks_diff(utime.ticks_ms(), start_wait_time) < 5000:
                            self.buttons['ok'].update()
                            if self.buttons['ok'].is_pressed():
                                break
                            utime.sleep_ms(20)
            utime.sleep_ms(50)


class CoinFlipApp(App):
    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.state = "IDLE"
        self.result = ""

    def run(self):
        self._active = True
        self.state = "IDLE"
        while self._active:
            for btn_obj in self.buttons.values():
                btn_obj.update()
            if self.state == "IDLE":
                self.display.clear()
                self.display.text("Coin Flip", (OLED_WIDTH - 9*8)//2, 10)
                self.display.text("Press OK to flip", (OLED_WIDTH - 16*8)//2, 30)
                self.display.text("UP/DOWN to exit", (OLED_WIDTH - 15*8)//2, 50)
                self.display.show()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                    self.state = "FLIPPING"
                    self.display.clear()
                    self.display.text("Flipping...", (OLED_WIDTH - 11*8)//2, 25)
                    self.display.show()
                    # Functional sounds for flipping
                    self.buzzer.play_tone(NOTES['C5'], 50)
                    self.buzzer.play_tone(NOTES['E5'], 50)
                    self.buzzer.play_tone(NOTES['G5'], 80)
                    self.buzzer._deinit_pwm()
                    utime.sleep_ms(300)
                    self.result = "Heads" if random.randint(0, 1) == 0 else "Tails"
                    self.state = "RESULT"
                elif self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)  # Exit sound
                    self.stop()
            elif self.state == "RESULT":
                self.display.clear()
                self.display.text(self.result, (OLED_WIDTH - len(self.result)*8)//2, 20)
                self.display.text("Press OK to exit", (OLED_WIDTH - 16*8)//2, 40)
                self.display.show()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)  # OK sound
                    self.stop()
            utime.sleep_ms(50)


class TemperatureApp(App):
    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.state = "IDLE"
        self.temp_c = 0.0
        self.temp_f = 0.0
        try:
            self.sensor_temp = machine.ADC(TEMP_SENSOR_ADC_CHANNEL)
        except Exception as e:
            print(f"Error initializing temperature sensor: {e}")
            self.sensor_temp = None
            self.state = "ERROR"

    def _read_temperature(self):
        if self.sensor_temp is None:
            return False, 0.0, 0.0
        try:
            adc_value = self.sensor_temp.read_u16()
            adc_voltage = adc_value * (3.3 / 65535)
            temp_c_raw = 27.0 - (adc_voltage - 0.706) / 0.001721
            self.temp_c = round(temp_c_raw - TEMPERATURE_OFFSET, 1)
            self.temp_f = round(self.temp_c * 9/5 + 32, 1)
            return True, self.temp_c, self.temp_f
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return False, 0.0, 0.0

    def run(self):
        self._active = True
        if self.state == "ERROR":
            self.display.show_message(["Temp Sensor", "Error!", "Press OK"], title="ERROR")
            while self._active:
                self.buttons['ok'].update()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                    self.stop()
                utime.sleep_ms(50)
            return

        self.state = "IDLE"
        while self._active:
            for btn_obj in self.buttons.values():
                btn_obj.update()
            if self.state == "IDLE":
                self.display.clear()
                self.display.text("Temperature", (OLED_WIDTH - 11*8)//2, 5)
                self.display.text("OK: Read", (OLED_WIDTH - 8*8)//2, 25)
                self.display.text("UP/DOWN: Exit", (OLED_WIDTH - 13*8)//2, 45)
                self.display.show()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                    self.state = "READING"
                    self.display.clear()
                    self.display.text("Reading temp...", (OLED_WIDTH - 15*8)//2, 25)
                    self.display.show()
                    utime.sleep_ms(100)
                    success, self.temp_c, self.temp_f = self._read_temperature()
                    if success:
                        self.state = "RESULT"
                    else:
                        self.state = "READ_ERROR"
                elif self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
                    self.stop()
            elif self.state == "READING":
                pass
            elif self.state == "RESULT":
                temp_str_c = f"{self.temp_c:.1f}C"
                temp_str_f = f"{self.temp_f:.1f}F"
                combined_str = f"{temp_str_c} / {temp_str_f}"
                self.display.clear()
                self.display.text("Temperature:", (OLED_WIDTH - 12*8)//2, 5)
                if len(combined_str) * 8 > OLED_WIDTH - 10:
                    self.display.text(temp_str_c, (OLED_WIDTH - len(temp_str_c)*8)//2, 20)
                    self.display.text(temp_str_f, (OLED_WIDTH - len(temp_str_f)*8)//2, 35)
                else:
                    self.display.text(combined_str, (OLED_WIDTH - len(combined_str)*8)//2, 25)
                self.display.text("OK:Exit UP:Read", 0, 50)
                self.display.show()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                    self.stop()
                elif self.buttons['up'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
                    self.state = "IDLE"
                    self.display.clear()
                    self.display.text("Reading Temp...", (OLED_WIDTH - 15*8)//2, 25)
                    self.display.show()  # Corrected message
                    utime.sleep_ms(200)
            elif self.state == "READ_ERROR":
                self.display.show_message(["Read Error", "Press OK"], title="Temp")
                read_error_start_time = utime.ticks_ms()
                while self._active and utime.ticks_diff(utime.ticks_ms(), read_error_start_time) < 5000:
                    self.buttons['ok'].update()
                    if self.buttons['ok'].is_pressed():
                        if App._menu_buzzer_enabled and self.buzzer:
                            self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                        self.state = "IDLE"
                        break
                    utime.sleep_ms(50)
                if self.state == "READ_ERROR":
                    self.state = "IDLE"
            utime.sleep_ms(50)


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


class ClockApp(App):
    _current_h = 0
    _current_m = 0
    _current_s = 0
    _ref_h = 0
    _ref_m = 0
    _ref_s = 0
    _base_tick_ms = 0
    _time_is_set = False
    _last_sec_disp = -1

    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.cfg = {"set": "Set Time", "disp_set": "Show Time", "disp_not_set": "Show Time (N)", "back": "Back"}
        self._update_menu()
        self.sel = 0
        self.state = "MENU"
        self.th = ClockApp._current_h
        self.tm = ClockApp._current_m
        self.ts = ClockApp._current_s
        self._update_time()

    def _update_menu(self):
        self.items = [self.cfg["disp_set" if ClockApp._time_is_set else "disp_not_set"], self.cfg["set"], self.cfg["back"]]

    def _update_time(self):
        if ClockApp._time_is_set:
            el_ms = utime.ticks_diff(utime.ticks_ms(), ClockApp._base_tick_ms)
            tot_ref_s = ClockApp._ref_h*3600 + ClockApp._ref_m*60 + ClockApp._ref_s
            cur_tot_s = tot_ref_s + (el_ms//1000)
            ClockApp._current_s = cur_tot_s % 60
            cur_tot_m = cur_tot_s//60
            ClockApp._current_m = cur_tot_m % 60
            ClockApp._current_h = (cur_tot_m//60) % 24

    def _disp_time_oled(self, setting=False):
        self.display.clear()
        y_off = 5
        sc_h = 16
        if setting:
            h, m, s = (f"[{self.th:02d}]" if self.state == "SET_HH" else f"{self.th:02d}"), \
                (f"[{self.tm:02d}]" if self.state == "SET_MM" else f"{self.tm:02d}"), \
                (f"[{self.ts:02d}]" if self.state == "SET_SS" else f"{self.ts:02d}")
            ts = f"{h}:{m}:{s}"
            self.display.text("Set Time:", (OLED_WIDTH-9*8)//2, y_off)
            y_off += self.display.text_height+self.display.line_padding+5
            tx = (OLED_WIDTH-len(ts)*8)//2
            self.display.text(ts, tx if tx > 0 else 0, y_off)
            instr_y = OLED_HEIGHT-self.display.text_height-2
            if self.state == "SET_HH":
                self.display.text("OK:MM UD:Hr", 0, instr_y)
            elif self.state == "SET_MM":
                self.display.text("OK:SS UD:Min", 0, instr_y)
            elif self.state == "SET_SS":
                self.display.text("OK:Save UD:Sec", 0, instr_y)
        else:
            self._update_time()
            ts = f"{ClockApp._current_h:02d}:{ClockApp._current_m:02d}:{ClockApp._current_s:02d}"
            scl = 2
            sc_w = 8*scl
            ts_w_sc = len(ts)*sc_w
            tx_sc = (OLED_WIDTH-ts_w_sc)//2
            ty_sc = (OLED_HEIGHT-sc_h)//2
            self.display.text_scaled(ts, tx_sc if tx_sc > 0 else 0, ty_sc, scl)
            if not ClockApp._time_is_set:
                nsy = ty_sc+sc_h+self.display.line_padding+2
                if nsy+self.display.text_height > OLED_HEIGHT:
                    nsy = ty_sc-self.display.text_height-self.display.line_padding-2
                self.display.text("Time not set!", (OLED_WIDTH-13*8)//2, nsy if nsy > 0 else OLED_HEIGHT-self.display.text_height-2)
            self.display.text("OK: Back", (OLED_WIDTH-8*8)//2, OLED_HEIGHT-self.display.text_height-2)
        self.display.show()

    def _run_set_time(self):
        pressed = False
        if self.buttons['up'].is_pressed():
            pressed = True
            if self.state == "SET_HH":
                self.th = (self.th+1) % 24
            elif self.state == "SET_MM":
                self.tm = (self.tm+1) % 60
            elif self.state == "SET_SS":
                self.ts = (self.ts+1) % 60
            if App._menu_buzzer_enabled and self.buzzer:
                self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
        elif self.buttons['down'].is_pressed():
            pressed = True
            if self.state == "SET_HH":
                self.th = (self.th-1+24) % 24
            elif self.state == "SET_MM":
                self.tm = (self.tm-1+60) % 60
            elif self.state == "SET_SS":
                self.ts = (self.ts-1+60) % 60
            if App._menu_buzzer_enabled and self.buzzer:
                self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
        elif self.buttons['ok'].is_pressed():
            pressed = True
            if App._menu_buzzer_enabled and self.buzzer:
                self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
            if self.state == "SET_HH":
                self.state = "SET_MM"
            elif self.state == "SET_MM":
                self.state = "SET_SS"
            elif self.state == "SET_SS":
                ClockApp._ref_h, ClockApp._ref_m, ClockApp._ref_s = self.th, self.tm, self.ts
                ClockApp._base_tick_ms = utime.ticks_ms()
                ClockApp._time_is_set = True
                self._update_time()
                self.state = "MENU"
                self._update_menu()
                self.display.show_message("Time Saved!", "Clock", 1.5)
                ClockApp._last_sec_disp = -1
                return
        if pressed or ClockApp._last_sec_disp == -1:
            self._disp_time_oled(True)
            ClockApp._last_sec_disp = 0

    def _run_disp_time(self):
        self._update_time()
        if ClockApp._current_s != ClockApp._last_sec_disp or ClockApp._last_sec_disp == -1:
            self._disp_time_oled(False)
            ClockApp._last_sec_disp = ClockApp._current_s
        if self.buttons['ok'].is_pressed() or self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed():
            if self.buttons['ok'].is_pressed() and App._menu_buzzer_enabled and self.buzzer:
                self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
            elif (self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed()) and App._menu_buzzer_enabled and self.buzzer:
                self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
            self.state = "MENU"
            ClockApp._last_sec_disp = -1

    def run(self):
        self._active = True
        ClockApp._last_sec_disp = -1
        self.state = "MENU"
        self._update_menu()
        self.sel = 0
        while self._active:
            for btn in self.buttons.values():
                btn.update()
            if self.state == "MENU":
                if ClockApp._time_is_set:
                    self._update_time()
                self.display.draw_menu(self.items, self.sel, title="Clock")
                new_sel, ok = self._handle_input_for_menu(len(self.items), self.sel)
                if new_sel != self.sel:
                    self.sel = new_sel
                if ok:
                    sel_title = self.items[self.sel]
                    ClockApp._last_sec_disp = -1
                    if sel_title == self.cfg["set"]:
                        self.state = "SET_HH"
                        self._update_time()
                        self.th, self.tm, self.ts = ClockApp._current_h, ClockApp._current_m, ClockApp._current_s
                    elif sel_title == self.cfg["disp_set"] or sel_title == self.cfg["disp_not_set"]:
                        self.state = "DISPLAY_TIME"
                    elif sel_title == self.cfg["back"]:
                        self.stop()
            elif self.state in ["SET_HH", "SET_MM", "SET_SS"]:
                self._run_set_time()
            elif self.state == "DISPLAY_TIME":
                self._run_disp_time()
            utime.sleep_ms(50)


class TelephoneApp(App):
    _phone_number_str = "         "
    _number_is_set = False

    def __init__(self, display_manager, buttons, buzzer_control):
        super().__init__(display_manager, buttons, buzzer_control)
        self.state = "MENU"
        self.items = []
        self._update_menu()
        self.sel = 0
        self.tmp_digits = list(TelephoneApp._phone_number_str)
        self.edit_idx = 0
        self.confirm_choice = 0

    def _update_menu(self): self.items = ["View Number", "Edit Number" if TelephoneApp._number_is_set else "Set Number", "Back"]

    def _disp_num_view(self):
        self.display.clear()
        self.display.text("Phone Number:", (OLED_WIDTH-13*8)//2, 5)
        if TelephoneApp._number_is_set:
            ns = TelephoneApp._phone_number_str
            ds = f"{ns[0:3]}-{ns[3:6]}-{ns[6:9]}"
            self.display.text(ds, (OLED_WIDTH-len(ds)*8)//2, 25)
        else:
            self.display.text("Not Set", (OLED_WIDTH-7*8)//2, 25)
        self.display.text("OK: Back", (OLED_WIDTH-8*8)//2, OLED_HEIGHT-self.display.text_height-5)
        self.display.show()

    def _disp_set_num_ui(self):
        self.display.clear()
        self.display.text("Set Number", (OLED_WIDTH-10*8)//2, 5)
        sdl = []
        for i in range(9):
            dc = self.tmp_digits[i]
            if i == self.edit_idx:
                sdl.append(f"[{dc}]")
            else:
                sdl.append(dc)
        rs = "".join(sdl)
        self.display.text(rs, (OLED_WIDTH-len(rs)*8-(rs.count('[')*8))//2, 25)  # Approx center
        self.display.text("UP/DN: Change", 0, 40)
        self.display.text("OK: Next Digit", 0, 50)
        self.display.show()

    def _disp_confirm_ui(self):
        self.display.clear()
        self.display.text("Save Number?", (OLED_WIDTH-12*8)//2, 5)
        ns = "".join(self.tmp_digits)
        ds = f"{ns[0:3]}-{ns[3:6]}-{ns[6:9]}"
        self.display.text(ds, (OLED_WIDTH-len(ds)*8)//2, 20)
        yp = "> " if self.confirm_choice == 0 else "  "
        np = "> " if self.confirm_choice == 1 else "  "
        self.display.text(f"{yp}Yes", 20, 40)
        self.display.text(f"{np}No", OLED_WIDTH//2+10, 40)
        self.display.show()

    def run(self):
        self._active = True
        self.state = "MENU"
        self._update_menu()
        self.sel = 0
        while self._active:
            for btn in self.buttons.values():
                btn.update()
            if self.state == "MENU":
                self.display.draw_menu(self.items, self.sel, title="Telephone")
                new_sel, ok = self._handle_input_for_menu(len(self.items), self.sel)
                self.sel = new_sel
                if ok:
                    st = self.items[self.sel]
                    if st == "View Number":
                        self.state = "VIEW_NUMBER"
                    elif st == "Set Number" or st == "Edit Number":
                        self.tmp_digits = list(TelephoneApp._phone_number_str)
                        self.edit_idx = 0
                        self.state = "SET_DIGIT"
                    elif st == "Back":
                        self.stop()
            elif self.state == "VIEW_NUMBER":
                self._disp_num_view()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)
                    self.state = "MENU"
            elif self.state == "SET_DIGIT":
                self._disp_set_num_ui()
                if self.buttons['up'].is_pressed():
                    cv = int(self.tmp_digits[self.edit_idx] if self.tmp_digits[self.edit_idx] != ' ' else '0')
                    self.tmp_digits[self.edit_idx] = str((cv+1) % 10)
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
                elif self.buttons['down'].is_pressed():
                    cv = int(self.tmp_digits[self.edit_idx] if self.tmp_digits[self.edit_idx] != ' ' else '0')
                    self.tmp_digits[self.edit_idx] = str((cv-1+10) % 10)
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
                elif self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['E5'], 40, duty_u16=9000)
                    if self.tmp_digits[self.edit_idx] == ' ':
                        self.tmp_digits[self.edit_idx] = '0'
                    if self.edit_idx < 8:
                        self.edit_idx += 1
                    else:
                        self.state = "CONFIRM_SAVE"
                        self.confirm_choice = 0
            elif self.state == "CONFIRM_SAVE":
                self._disp_confirm_ui()
                if self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed():
                    self.confirm_choice = 1-self.confirm_choice
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)
                elif self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_tone(NOTES['G5'], 60, duty_u16=12000)  # Save/Cancel confirm sound
                    if self.confirm_choice == 0:
                        for i in range(9):
                            if self.tmp_digits[i] == ' ':
                                self.tmp_digits[i] = '0'
                        TelephoneApp._phone_number_str = "".join(self.tmp_digits)
                        TelephoneApp._number_is_set = True
                        self.display.show_message("Number Saved!", "Telephone", 1.5)
                    else:
                        self.display.show_message("Not Saved", "Telephone", 1.5)
                    self.state = "MENU"
                    self._update_menu()
                    self.sel = 0
            utime.sleep_ms(50)


def main():
    i2c = machine.I2C(OLED_I2C_ID, scl=machine.Pin(OLED_SCL_PIN_NUM), sda=machine.Pin(OLED_SDA_PIN_NUM))
    try:
        oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_I2C_ADDR)
        oled.fill(0)
        oled.text("Loading...", 0, 0)
        oled.show()
        utime.sleep_ms(500)
    except Exception as e:
        print(f"OLED Error: {e}")

    display = DisplayManager(oled)
    sleep_manager = SleepManager(SLEEP_SWITCH_PIN_NUM)
    buttons_map = {
        'up': Button(BUTTON_UP_PIN_NUM),
        "down": Button(BUTTON_DOWN_PIN_NUM),
        "ok": Button(BUTTON_OK_PIN_NUM)
    }
    buzzer = Buzzer(BUZZER_PIN_NUM, App._menu_buzzer_enabled)

    apps_list = [
        {"name": "Music Player", "app_class": MusicApp},
        {"name": "Coin Flip", "app_class": CoinFlipApp},
        {"name": "Temperature", "app_class": TemperatureApp},
        {"name": "Matrix", "app_class": MatrixEffectsApp},
        {"name": "Clock", "app_class": ClockApp},
        {"name": "Telephone", "app_class": TelephoneApp},
        {"name": "Settings", "app_class": SettingsApp}
    ]

    app_titles = [app["name"] for app in apps_list]
    current_sel_main = 0
    display.show_message("Watch 2.0 Beta", title="Welcome!", duration_s=1)

    while True:
        if sleep_manager.should_sleep():
            sleep_manager.enter_sleep_mode(display, buzzer)
        else:
            sleep_manager.exit_sleep_mode(display)

        for btn in buttons_map.values():
            btn.update()
        display.draw_menu(app_titles, current_sel_main, title="MAIN MENU")

        if buttons_map['up'].is_pressed():
            current_sel_main = (current_sel_main - 1 + len(app_titles)) % len(app_titles)
            if App._menu_buzzer_enabled:
                buzzer.play_exit_sound()
        elif buttons_map['down'].is_pressed():
            current_sel_main = (current_sel_main + 1) % len(app_titles)
            if App._menu_buzzer_enabled:
                buzzer.play_exit_sound()
        elif buttons_map['ok'].is_pressed():
            if App._menu_buzzer_enabled:
                buzzer.play_ok_sound()

            selected_app_cfg = apps_list[current_sel_main]
            app_cls = selected_app_cfg["app_class"]
            display.show_message("Loading...", title=selected_app_cfg['name'], duration_s=0.2, clear_after=True)

            # for _ in range(5):  # Debounce before app start
            #     for btn in buttons_map.values():
            #         btn.update()
            #     utime.sleep_ms(10)

            app_instance = app_cls(display, buttons_map, buzzer)
            app_instance.run()

            # for _ in range(5):  # Debounce after app exit
            #     for btn in buttons_map.values():
            #         btn.update()
            #     utime.sleep_ms(10)

            display.clear()
            display.show()

        utime.sleep_ms(50)


if __name__ == "__main__":
    main()
