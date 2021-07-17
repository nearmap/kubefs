import curses
import os
import signal
from typing import Sequence

import _curses

from kube.channels.objects import OEvReceiver


class Display:
    def __init__(self, *, oev_receivers: Sequence[OEvReceiver]):
        self.oev_receivers = oev_receivers

        self.screen = None
        self.objs = []

    def start(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        self.screen.timeout(10)

        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        signal.signal(signal.SIGWINCH, self.on_resize)

        self.mainloop()

    def should_exit(self):
        try:
            if self.screen.getkey() == "q":
                return True
        except _curses.error:
            pass

        return False

    def draw(self):
        curses.update_lines_cols()
        curses.curs_set(False)

        self.screen.clear()
        # cols, lines = os.get_terminal_size()
        # curses.resizeterm(lines, cols)

        try:
            for obj in self.objs:
                self.screen.addstr("%s\n" % obj["metadata"]["name"])
        except curses.error:
            pass

    def on_resize(self, signum, frame):
        # with open('log', 'w') as fl:
        #     fl.write("%s" % signum)

        cols, lines = os.get_terminal_size()
        curses.resizeterm(lines, cols)

        self.draw()
        # self.should_exit()

    def mainloop(self):
        while True:
            for receiver in self.oev_receivers:
                event = receiver.recv_nowait()
                if event:
                    self.objs.append(event.object)

            self.draw()

            if self.should_exit():
                break
