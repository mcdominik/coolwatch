import machine
import utime


class SleepManager:
    """Handles RP2040-Matrix sleep mode functionality"""

    def __init__(self, sleep_pin_num):
        self.sleep_pin = machine.Pin(sleep_pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
        self.is_sleeping = False

    def should_sleep(self):
        """Check if device should enter sleep mode (pin LOW = switch closed = sleep)"""
        return self.sleep_pin.value() == 0

    def try_enter_sleep_mode(self, display_manager, buzzer_control):
        """Enter sleep mode improving battery life"""
        if self.is_sleeping:
            return

        print("Entering sleep mode...")
        display_manager.clear_and_draw("Sleep mode..", 20, 25)
        utime.sleep_ms(500)

        self.is_sleeping = True
        display_manager.oled.poweroff()

        if buzzer_control:
            buzzer_control.stop_tone()

    def try_exit_sleep_mode(self, display_manager):
        """Exit sleep mode"""
        if not self.is_sleeping:
            return

        print("Exiting sleep mode..")
        self.is_sleeping = False
        display_manager.oled.poweron()
        display_manager.clear_and_draw("Waking up...", 20, 25)
        utime.sleep_ms(500)
