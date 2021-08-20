import contextlib
import enum
from collections import defaultdict
from typing import DefaultDict, Iterator, List, Optional, Tuple

from colored import bg, fg
from colored.colored import stylize

from podview.model.colors import Color


class TextAlign(enum.Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class ColorSpan:
    def __init__(
        self, offset: int, length: int, fg_col: str = "", bg_col: str = ""
    ) -> None:
        self.offset = offset
        self.length = length
        self.fg_col = fg_col
        self.bg_col = bg_col

        self.styles = []
        if fg_col:
            self.styles.append(fg(fg_col))
        if bg_col:
            self.styles.append(bg(bg_col))


class ScreenBuffer:
    """
    Represents a buffer of lines of text. The buffer is of unlimited size and
    thus allows to grow taller or wider than the size of the viewport. This
    allows implementing scrolling behavior by rendering a section of the buffer
    onto the viewing surface using dimensions and an offset.
    """

    def __init__(self, fillchar=" ") -> None:
        self.pos_x = 0
        self.pos_y = 0
        self.indents: List[int] = []

        self.fillchar = fillchar
        self.lines = [self.create_blank_line()]
        self.colspans: DefaultDict[int, List[ColorSpan]] = defaultdict(list)

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
        width: int = 0,
        color: Optional[Color] = None,
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

        if color is not None:
            colspan = ColorSpan(
                offset=len(before) + start_pos,
                length=len(text),
                fg_col=color.fg,
                bg_col=color.bg,
            )
            self.colspans[self.pos_y].append(colspan)

        self.pos_x = indent + width

    @contextlib.contextmanager
    def indent(self, width: int) -> Iterator[None]:
        try:
            intended_pos = self.pos_x + width
            incremental = intended_pos - sum(self.indents)
            if incremental < 0:
                incremental = width

            self.indents.append(incremental)

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

            line = line[offset_x : offset_x + dim_x]
            for colspan in self.colspans[y]:
                begin_index = colspan.offset - offset_x
                end_index = begin_index + colspan.length

                if begin_index > dim_x:
                    continue

                if begin_index < 0:
                    begin_index = 0
                if end_index > dim_x:
                    end_index = dim_x

                segment = line[begin_index:end_index]
                segment = stylize(text=segment, styles=colspan.styles, reset=True)

                line = line[:begin_index] + segment + line[end_index:]

            line = border_vert + line + border_vert
            lines.append(line)

        if border_horiz:
            length = dim_x + 2 if border_vert else dim_x
            line = border_horiz * length
            lines = [line] + lines + [line]

        block = "\n".join(lines)
        return block


if __name__ == "__main__":
    buf = ScreenBuffer(fillchar=" ")
    buf.write(text="cluster-one", color=Color(bg="dodger_blue_1", fg="white"))

    with buf.indent(width=2):
        buf.write(text="pod-name-1")
        with buf.indent(width=6):
            buf.write(text="running")
            with buf.indent(width=3):
                buf.write(text="2 min")

        with buf.indent(width=2):
            buf.write(text="cont-name-1")
            with buf.indent(width=4):
                buf.write(text="terminated")

            buf.write(text="cont-name-2")
            with buf.indent(width=4):
                buf.write(text="running")

        buf.write(text="pod-name-2")
        with buf.indent(width=6):
            buf.write(text="running")
            with buf.indent(width=3):
                buf.write(text="2 min")

        with buf.indent(width=2):
            buf.write(text="cont-name-1")
            buf.end_line()

            buf.write(text="cont-name-2")
            buf.end_line()

    buf.write(text="cluster-two", color=Color(bg="indian_red_1a", fg="white"))

    print(buf.assemble(dim=(80, 24), offset=(0, 0), border_horiz="-", border_vert="|"))
