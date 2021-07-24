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
        self.screen = None
        self.buffer: ScreenBuffer = None
        self.logger = logger or logging.getLogger("display")

    def initialize(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.use_default_colors()

        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        # don't display cursor
        curses.curs_set(False)

        # ms timeout for reading key presses
        self.screen.timeout(10)

        signal.signal(signal.SIGWINCH, self.on_resize)

    def exit(self):
        curses.endwin()

    def should_exit(self):
        try:
            if self.screen.getkey() == "q":
                # if self.screen.getkey():
                return True
        except _curses.error:
            pass

        return False

    def redraw(self):
        self.screen.clear()

        cols, lines = os.get_terminal_size()
        dim = (cols - 1, lines)
        block = self.buffer.assemble(dim=dim)

        try:
            self.screen.addstr(block)
        except curses.error:
            self.logger.exception("Failed to redraw screen")
            raise CursesDisplayError()

    def on_resize(self, signum, frame):
        cols, lines = os.get_terminal_size()
        curses.resizeterm(lines, cols)

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

        return False


if __name__ == "__main__":
    d = CursesDisplay(oev_receivers=None)
    d.initialize()
    d.mainloop()
