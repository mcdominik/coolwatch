import utime

from src.apps.app import App
from src.constants import NOTES


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
