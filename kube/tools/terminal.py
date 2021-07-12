import sys

import colored
from colored import stylize


class TerminalPrinter:
    def loudln(self, msg):
        msg = stylize(msg, styles=[colored.bg("magenta"), colored.fg("white")])
        self.write_line(msg)

    def write_line(self, msg):
        self.write("%s\n" % msg)

    def write(self, msg):
        sys.stdout.write(msg)
        sys.stdout.flush()
