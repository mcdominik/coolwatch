import utime

from src.apps.app import App
from constants import NOTES, OLED_HEIGHT, OLED_WIDTH


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
                    self.confirm_choice = 1 - self.confirm_choice
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
