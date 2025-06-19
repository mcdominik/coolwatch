from src.constants import NOTES


class App:
    _menu_buzzer_enabled = True

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
