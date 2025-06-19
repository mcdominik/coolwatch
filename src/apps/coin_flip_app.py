import random
import utime

from src.apps.app import App
from src.constants import NOTES, OLED_WIDTH


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
                    self.display.clear_and_draw("Flipping...", (OLED_WIDTH - 11*8)//2, 25)
                    # self.display.clear()
                    # self.display.text("Flipping...", (OLED_WIDTH - 11*8)//2, 25)
                    # self.display.show()
                    # Functional sounds for flipping
                    self.buzzer.play_flip_sound()
                    # self.buzzer.play_tone(NOTES['C5'], 50)
                    # self.buzzer.play_tone(NOTES['E5'], 50)
                    # self.buzzer.play_tone(NOTES['G5'], 80)
                    # self.buzzer._deinit_pwm()
                    # TODO inspect this sleep
                    # utime.sleep_ms(300)
                    self.result = "Heads" if random.randint(0, 1) == 0 else "Tails"
                    self.state = "RESULT"
                elif self.buttons['up'].is_pressed() or self.buttons['down'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_exit_sound()
                        # self.buzzer.play_tone(NOTES['C5'], 30, duty_u16=8000)  # Exit sound
                    self.stop()
            elif self.state == "RESULT":
                self.display.clear()
                self.display.text(self.result, (OLED_WIDTH - len(self.result)*8)//2, 20)
                self.display.text("Press OK to exit", (OLED_WIDTH - 16*8)//2, 40)
                self.display.show()
                if self.buttons['ok'].is_pressed():
                    if App._menu_buzzer_enabled and self.buzzer:
                        self.buzzer.play_ok_sound()
                        # self.buzzer.play_tone(NOTES['E5'], 50, duty_u16=10000)  # OK sound
                    self.stop()
            utime.sleep_ms(50)
