import random
from typing import List

import colored
import colored.colors

from kube.config import Context


class Color:
    def __init__(self, fg: str, bg: str = "") -> None:
        # fg/bg are human readable names as defined by 'colored'
        self.fg = fg
        self.bg = bg

    def __eq__(self, other) -> bool:
        return all((self.fg == other.fg, self.bg == other.bg))

    def __hash__(self) -> int:
        return hash(self.fg) + hash(self.bg)

    @property
    def bg_id(self) -> int:
        if self.bg:
            return colored.colors.names.index(self.bg.upper())

        return -1

    @property
    def fg_id(self) -> int:
        return colored.colors.names.index(self.fg.upper())


class ColorPicker:
    _instance = None

    _error_color = Color(fg="indian_red_1b")
    _warn_color = Color(fg="dark_orange")

    _dim_color = Color(fg="grey_70")

    _waiting_color = Color(fg="gold_3b")
    _in_progress_color = Color(fg="sky_blue_3")
    _stopped_color = Color(fg="dark_gray")
    _succeeded_color = Color(fg="cyan")

    _context_colors = (
        Color(bg="dodger_blue_1", fg="white"),
        Color(bg="indian_red_1a", fg="white"),
        Color(bg="chartreuse_3a", fg="white"),
        Color(bg="royal_blue_1", fg="white"),
        Color(bg="light_pink_3", fg="white"),
        Color(bg="green_3b", fg="white"),
    )

    _pod_phase_colors = {
        "pending": _waiting_color,
        "running": _in_progress_color,
        "succeeded": _succeeded_color,
        "failed": _error_color,
        "unknown": _stopped_color,
        "deleted": _stopped_color,
    }

    _container_name_color = _dim_color

    _container_state_colors = {
        "waiting": _waiting_color,
        "running": _in_progress_color,
        "terminated": _stopped_color,
    }

    # trying to pick colors that are not too saturated nor too dim
    _image_hash_ranges = [
        (33, 39),
        (69, 75),
        (77, 81),
        (99, 117),
        (130, 153),
        (166, 189),
        (209, 219),
    ]
    _image_hash_indices = []

    def __init__(self, contexts: List[Context]) -> None:
        self.contexts = contexts

        self.image_hash_colors = {}

        for lower, upper in self._image_hash_ranges:
            series = list(range(lower, upper + 1))
            self._image_hash_indices.extend(series)

    @classmethod
    def get_instance(cls, contexts: List[Context]) -> "ColorPicker":
        if cls._instance is None:
            cls._instance = cls(contexts)

        return cls._instance

    def get_error_color(self) -> Color:
        return self._error_color

    def get_warn_color(self) -> Color:
        return self._warn_color

    def get_for_context(self, context: Context) -> Color:
        return self._dim_color
        # idx = self.contexts.index(context) % len(self._context_colors)
        # return self._context_colors[idx]

    def get_for_pod_phase(self, phase: str) -> Color:
        return self._pod_phase_colors[phase]

    def get_for_container_name(self) -> Color:
        return self._container_name_color

    def get_for_container_state(self, state: str) -> Color:
        return self._container_state_colors[state]

    def get_for_image_hash(self, image_hash: str) -> Color:
        """Hash the image hash onto a color."""

        color = self.image_hash_colors.get(image_hash)

        if not color:
            idx = hash(image_hash) % len(self._image_hash_indices)
            name = colored.colors.names[idx].lower()
            color = Color(fg=name)
            self.image_hash_colors[image_hash] = color

        return color


if __name__ == "__main__":
    for idx, name in enumerate(colored.colors.names):
        name = name.lower()
        fg = colored.stylize(name, [colored.fg(name)])
        bg = colored.stylize(name, [colored.fg("white"), colored.bg(name)])

        print(f"{idx:3}    {fg}")
        # print(f'{idx}    {bg}')
        # print()
