
import framebuf
import utime


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

    # TODO implement this method
    def clear_and_draw(self, text, x, y):
        self.clear()
        self.text(text, x, y)
        self.show()

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
