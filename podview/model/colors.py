from typing import List

from kube.config import Context


class Color:
    def __init__(self, fg: str, bg: str = "") -> None:
        # fg/bg are human readable names as defined by 'colored'
        self.fg = fg
        self.bg = bg


class ColorPicker:
    _context_colors = (
        Color(bg="dodger_blue_1", fg="white"),
        Color(bg="indian_red_1a", fg="white"),
        Color(bg="chartreuse_3a", fg="white"),
        Color(bg="royal_blue_1", fg="white"),
        Color(bg="light_pink_3", fg="white"),
        Color(bg="green_3b", fg="white"),
    )

    def __init__(self, contexts: List[Context]) -> None:
        self.contexts = contexts

    def get_for_context(self, context: Context) -> Color:
        idx = self.contexts.index(context) % len(self._context_colors)
        return self._context_colors[idx]
