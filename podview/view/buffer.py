import contextlib
import enum
from typing import Tuple

from colored import bg, fg
from colored.colored import stylize


class TextAlign(enum.Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class ScreenBuffer:
    def __init__(self, *, dim: Tuple[int, int]) -> None:
        self.dim_x, self.dim_y = dim

        self.pos_x = 0
        self.pos_y = 0
        self.indents = []

        self.blank_char = " "
        self.lines = [self.create_blank_line()]

    def create_blank_line(self):
        return self.blank_char * self.dim_x

    def write(
        self,
        *,
        text: str,
        width: int = None,
        fg_col: str = None,
        bg_col: str = None,
        align: TextAlign = TextAlign.LEFT
    ) -> None:
        length = len(text)
        width = width or length
        indent = sum(self.indents) if self.indents else self.pos_x

        if width and length > width:
            raise RuntimeError(
                "Cannot write text %r that will not fit in width %r" % (text, width)
            )

        # if indent + width > self.dim_x:
        #     raise RuntimeError("Tried to write beyond width of the screen buffer")

        start_pos = 0
        if align is TextAlign.RIGHT:
            start_pos = width - length
        elif align is TextAlign.CENTER:
            start_pos = int((width - length) / 2)

        buf = " " * width
        buf = buf[:start_pos] + text + buf[start_pos + length :]
        assert len(buf) == width

        line = self.lines[self.pos_y]

        line = line[:indent] + buf + line[indent + width :]

        self.lines[self.pos_y] = line

        self.pos_x = indent + width

    def end_line(self) -> None:
        # if self.pos_y + 1 > len(self.lines) - 1:
        #     raise RuntimeError("Tried to write beyond height of the screen buffer")

        blank = self.create_blank_line()
        self.lines.append(blank)

        self.pos_x = 0
        self.pos_y += 1

    @contextlib.contextmanager
    def indent(self, width: int) -> None:
        try:
            width = self.pos_x + width
            self.indents.append(width)

            yield

        finally:
            self.indents.pop(-1)
            if not self.pos_x == 0:
                self.end_line()

    def assemble(self) -> str:
        lines = ["%s|" % line for line in self.lines if line.strip()]
        lines.append("-" * self.dim_x)
        block = "\n".join(lines)
        return block


if __name__ == "__main__":
    buf = ScreenBuffer(dim=(80, 24))
    buf.write(text="cluster-name")

    with buf.indent(width=2):
        buf.write(text="pod-name-1")
        buf.end_line()

        with buf.indent(width=2):
            buf.write(text="cont-name-1")
            buf.end_line()

            buf.write(text="cont-name-2")
            buf.end_line()

        buf.write(text="pod-name-2")
        buf.end_line()

        with buf.indent(width=2):
            buf.write(text="cont-name-1")
            buf.end_line()

            buf.write(text="cont-name-2")
            buf.end_line()

    buf.write(text="cluster-name")

    print(buf.assemble())
