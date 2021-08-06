import curses
import logging
import os
import signal
import time

import _curses

from podview.view.buffer import ScreenBuffer


class CursesDisplayError(Exception):
    pass


class CursesDisplay:
    def __init__(self, logger=None):
        self.window = None
        self.logger = logger or logging.getLogger(__name__)

        self.dim_x = 0
        self.dim_y = 0

        self.buffer: ScreenBuffer = None
        self.buffer_offset_x = 0
        self.buffer_offset_y = 0

    def initialize(self):
        self.window = curses.initscr()
        curses.start_color()
        curses.use_default_colors()

        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        # don't display cursor
        curses.curs_set(False)

        # ms timeout for reading key presses
        self.window.timeout(10)
        self.window.nodelay(1)
        self.window.keypad(True)

        self.dim_x, self.dim_y = os.get_terminal_size()

        signal.signal(signal.SIGWINCH, self.on_resize)

    def exit(self):
        curses.endwin()

    def should_exit(self):
        key = None

        try:
            key = self.window.getch()
        except _curses.error:
            pass

        if key not in (None, -1):
            if key == ord("q"):
                return True

            elif key == curses.KEY_LEFT:
                self.logger.info("Left arrow pressed")
                self.buffer_offset_x = max(0, self.buffer_offset_x - 1)
                self.redraw()

            elif key == curses.KEY_RIGHT:
                self.logger.info("Right arrow pressed")
                self.buffer_offset_x += 1
                self.redraw()

            elif key == curses.KEY_DOWN:
                self.logger.info("Down arrow pressed")
                self.buffer_offset_y += 1
                self.redraw()

            elif key == curses.KEY_UP:
                self.logger.info("Up arrow pressed")
                self.buffer_offset_y = max(0, self.buffer_offset_y - 1)
                self.redraw()

            elif key == curses.KEY_PPAGE:
                self.logger.info("Page Up pressed")
                self.buffer_offset_y = max(
                    0, self.buffer_offset_y - int(self.dim_y / 2)
                )
                self.redraw()

            elif key == curses.KEY_NPAGE:
                self.logger.info("Page Down pressed")
                self.buffer_offset_y += int(self.dim_y / 2)
                self.redraw()

            else:
                self.logger.info("Unmapped key pressed: %r", key)

        return False

    def redraw(self):
        self.window.clear()

        dim = (self.dim_x - 1, self.dim_y)
        offset = (self.buffer_offset_x, self.buffer_offset_y)
        block = self.buffer.assemble(dim=dim, offset=offset)

        try:
            self.window.addstr(block)
        except curses.error:
            self.logger.exception("Failed to redraw screen")
            raise CursesDisplayError()

    def on_resize(self, signum, frame):
        self.dim_x, self.dim_y = os.get_terminal_size()
        curses.resizeterm(self.dim_y, self.dim_x)

        self.redraw()

    def interact(self, buffer: ScreenBuffer, timeout: int) -> bool:
        self.buffer = buffer

        start_time = time.time()
        self.redraw()

        while True:
            if time.time() - start_time > timeout:
                break

            if self.should_exit():
                self.exit()
                return True

            time.sleep(timeout / 100)

        return False


if __name__ == "__main__":
    d = CursesDisplay(oev_receivers=None)
    d.initialize()
    d.mainloop()
