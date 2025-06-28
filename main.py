
import utime
import machine


from src.apps.clock_app import ClockApp
from src.apps.telephone_app import TelephoneApp
from src.apps.app import App
from src.apps.matrix_app import MatrixEffectsApp
from src.apps.music_app import MusicApp
from src.apps.temperature_app import TemperatureApp
from src.buzzer_controller import BuzzerController
from src.apps.coin_flip_app import CoinFlipApp
from src.display_manager import DisplayManager
from src.apps.settings_app import SettingsApp
from src.ssd1306 import SSD1306_I2C
from src.sleep_manager import SleepManager
from src.button import Button
from src.constants import (
    OLED_SDA_PIN_NUM,
    OLED_SCL_PIN_NUM,
    OLED_WIDTH,
    OLED_HEIGHT,
    OLED_I2C_ADDR,
    OLED_I2C_ID,
    BUZZER_PIN_NUM,
    BUTTON_UP_PIN_NUM,
    BUTTON_DOWN_PIN_NUM,
    BUTTON_OK_PIN_NUM,
    SLEEP_SWITCH_PIN_NUM,
)


def main():
    i2c = machine.I2C(OLED_I2C_ID, scl=machine.Pin(OLED_SCL_PIN_NUM), sda=machine.Pin(OLED_SDA_PIN_NUM))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_I2C_ADDR)
    oled.fill(0)
    try:
        oled.text("Loading...", 0, 0)
        oled.show()
        utime.sleep_ms(500)
    except Exception as e:
        oled.text("Error: {}".format(str(e)), 0, 0)
        oled.show()
        print(f"OLED Error: {e}")

    display = DisplayManager(oled)
    sleep_manager = SleepManager(SLEEP_SWITCH_PIN_NUM)
    buttons_map = {
        'up': Button(BUTTON_UP_PIN_NUM),
        "down": Button(BUTTON_DOWN_PIN_NUM),
        "ok": Button(BUTTON_OK_PIN_NUM)
    }
    buzzer = BuzzerController(BUZZER_PIN_NUM, App._menu_buzzer_enabled)

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
            sleep_manager.try_enter_sleep_mode(display, buzzer)
        else:
            sleep_manager.try_exit_sleep_mode(display)

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
