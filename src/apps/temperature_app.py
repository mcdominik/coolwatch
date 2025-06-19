
import utime
import machine

from src.apps.app import App
from constants import NOTES, OLED_WIDTH, TEMP_SENSOR_ADC_CHANNEL, TEMPERATURE_OFFSET


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
