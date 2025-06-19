import utime

from src.apps.app import App

from constants import BIRTHDAY_MELODY, IMPERIAL_MARCH_MELODY, PIRATES_MELODY


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
