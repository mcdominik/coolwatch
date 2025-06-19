import utime

from src.apps.app import App
from constants import NOTES, OLED_HEIGHT, OLED_WIDTH


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
