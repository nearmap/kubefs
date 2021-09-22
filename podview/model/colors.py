import logging
from typing import List

import colored
import colored.colors
from uhashring import HashRing

from kube.config import Context


class Color:
    def __init__(self, fg: str, bg: str = "") -> None:
        # fg/bg are human readable names as defined by 'colored'
        self.fg = fg
        self.bg = bg

        self.styles = self.create_styles()

    def create_styles(self) -> List[str]:
        styles = []

        if self.fg:
            styles.append(colored.fg(self.fg))
        if self.bg:
            styles.append(colored.bg(self.bg))

        return styles

    def __str__(self) -> str:
        # needed for HashRing because it hashes based on __str__
        return f"{self.__class__.__name__}(fg={self.fg}, bg={self.bg})"

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

    def stylize(self, text: str, reset: bool = True) -> str:
        return colored.stylize(text=text, styles=self.styles, reset=reset)


class ColorPicker:
    _instance = None

    _error_color = Color(fg="indian_red_1b")
    _warn_color = Color(fg="dark_orange")

    _dim_color = Color(fg="grey_70")
    _dimmer_color = Color(fg="grey_46")

    _waiting_color = Color(fg="gold_3b")
    _in_progress_color = Color(fg="deep_sky_blue_1")
    _dim_in_progress_color = Color(fg="light_sky_blue_3b")
    _stopped_color = Color(fg="dark_gray")
    _succeeded_color = Color(fg="cyan")

    _pod_phase_colors = {
        "pending": _waiting_color,
        "running": _in_progress_color,
        "succeeded": _succeeded_color,
        "failed": _error_color,
        "unknown": _stopped_color,
        "deleted": _stopped_color,
    }

    _init_container_name_color = _dimmer_color
    _std_container_name_color = _dim_color

    _container_state_colors = {
        "waiting": _waiting_color,
        "running": _dim_in_progress_color,
        "terminated": _stopped_color,
    }

    # indices into colored.colors.names
    # trying to pick colors that are not too bring nor too dim
    _image_hash_color_index_ranges = [
        (33, 39),
        (69, 75),
        (77, 80),
        (99, 117),
        (130, 153),
        (166, 189),
        (209, 219),
    ]

    def __init__(self, logger=None) -> None:
        colors = []

        for lower, upper in self._image_hash_color_index_ranges:
            for idx in range(lower, upper + 1):
                name = colored.colors.names[idx].lower()

                if "grey" in name:
                    continue  # gray is not useful for highlighting

                color = Color(fg=name)
                colors.append(color)

        self.image_hash_ring = HashRing(colors)

        self.logger = logger or logging.getLogger(__name__)

    @classmethod
    def get_instance(cls) -> "ColorPicker":
        if cls._instance is None:
            cls._instance = cls()

        return cls._instance

    def get_error_color(self) -> Color:
        return self._error_color

    def get_warn_color(self) -> Color:
        return self._warn_color

    def get_for_context(self, context: Context) -> Color:
        return self._dim_color

    def get_for_pod_phase(self, phase: str) -> Color:
        return self._pod_phase_colors[phase]

    def get_for_container_name_init(self) -> Color:
        return self._init_container_name_color

    def get_for_container_name_std(self) -> Color:
        return self._std_container_name_color

    def get_for_container_state(self, state: str) -> Color:
        return self._container_state_colors[state]

    def get_for_image_hash(self, image_hash: str) -> Color:
        """Consistently hashes the image hash onto a color."""
        return self.image_hash_ring.get_node(image_hash)


if __name__ == "__main__":
    import pprint

    if 1:
        for idx, name in enumerate(colored.colors.names):
            name = name.lower()
            fg = colored.stylize(name, [colored.fg(name)])
            bg = colored.stylize(name, [colored.fg("white"), colored.bg(name)])

            print(f"{idx:3}    {fg}")
            # print(f'{idx}    {bg}')
            # print()

    elif 0:
        picker = ColorPicker()
        for node in picker.image_hash_ring._nodes:
            print(f"image:{node.stylize(node.fg)}")

    else:
        picker = ColorPicker()
        pprint.pprint(picker.image_hash_ring._nodes)
