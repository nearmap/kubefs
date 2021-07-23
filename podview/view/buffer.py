import contextlib
import enum
from typing import Iterator, List, Tuple

from colored import bg, fg
from colored.colored import stylize


class TextAlign(enum.Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class ScreenBuffer:
    def __init__(self, fillchar=" ") -> None:
        self.pos_x = 0
        self.pos_y = 0
        self.indents: List[int] = []

        self.fillchar = fillchar
        self.lines = [self.create_blank_line()]

    def create_blank_line(self):
        return ""

    def end_line(self) -> None:
        self.lines.append(self.create_blank_line())

        self.pos_x = 0
        self.pos_y += 1

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
        width = max(width, length) if width else length
        indent = sum(self.indents) if self.indents else self.pos_x

        start_pos = 0
        if align is TextAlign.RIGHT:
            start_pos = width - length
        elif align is TextAlign.CENTER:
            start_pos = int((width - length) / 2)

        buf = self.fillchar * width
        buf = buf[:start_pos] + text + buf[start_pos + length :]
        assert len(buf) == width

        line = self.lines[self.pos_y]

        before = line[:indent]
        if len(before) < indent:
            deficit = indent - len(before)
            before = before + self.fillchar * deficit

        line = before + buf

        self.lines[self.pos_y] = line

        self.pos_x = indent + width

    @contextlib.contextmanager
    def indent(self, width: int) -> Iterator[None]:
        try:
            width = self.pos_x + width
            self.indents.append(width)

            yield

        finally:
            self.indents.pop(-1)
            if not self.pos_x == 0:
                self.end_line()

    def assemble(
        self,
        dim: Tuple[int, int],
        offset: Tuple[int, int] = (0, 0),
        border_horiz="",
        border_vert="",
    ) -> str:
        dim_x, dim_y = dim
        offset_x, offset_y = offset

        source_lines = self.lines

        if len(source_lines) < dim_y + offset_y:
            deficit = dim_y + offset_y - len(source_lines)
            source_lines.extend([self.create_blank_line()] * deficit)

        lines: List[str] = []
        for y, line in enumerate(source_lines):
            if y < offset_y:
                continue

            if len(lines) >= dim_y:
                break

            if len(line) < dim_x + offset_x:
                deficit = dim_x + offset_x - len(line)
                line = line + self.fillchar * deficit

            line = border_vert + line[offset_x : offset_x + dim_x] + border_vert
            lines.append(line)

        if border_horiz:
            length = dim_x + 2 if border_vert else dim_x
            line = border_horiz * length
            lines = [line] + lines + [line]

        block = "\n".join(lines)
        return block


if __name__ == "__main__":
    buf = ScreenBuffer(fillchar=" ")
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

    print(buf.assemble(dim=(80, 25), offset=(0, 0), border_horiz="-", border_vert="|"))
