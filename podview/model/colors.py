import random
from typing import List

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

    _context_colors = (
        Color(bg="dodger_blue_1", fg="white"),
        Color(bg="indian_red_1a", fg="white"),
        Color(bg="chartreuse_3a", fg="white"),
        Color(bg="royal_blue_1", fg="white"),
        Color(bg="light_pink_3", fg="white"),
        Color(bg="green_3b", fg="white"),
    )

    _pod_phase_colors = {
        "pending": Color(fg="yellow"),
        "running": Color(fg="green"),
        "succeeded": Color(fg="cyan"),
        "failed": Color(fg="red"),
        "unknown": Color(fg="dark_gray"),
        "deleted": Color(fg="dark_gray"),
    }

    _container_state_colors = {
        "waiting": Color(fg="yellow"),
        "running": Color(fg="green"),
        "terminated": Color(fg="dark_gray"),
    }

    def __init__(self, contexts: List[Context]) -> None:
        self.contexts = contexts

        self.image_hash_colors = {}

    @classmethod
    def get_instance(cls, contexts: List[Context]) -> "ColorPicker":
        if cls._instance is None:
            cls._instance = cls(contexts)

        return cls._instance

    def get_for_context(self, context: Context) -> Color:
        idx = self.contexts.index(context) % len(self._context_colors)
        return self._context_colors[idx]

    def get_for_pod_phase(self, phase: str) -> Color:
        return self._pod_phase_colors[phase]

    def get_for_container_state(self, state: str) -> Color:
        return self._container_state_colors[state]

    def get_for_image_hash(self, hash: str) -> Color:
        """Hash the image hash onto a color."""

        color = self.image_hash_colors.get(hash)

        if not color:
            idx = random.randint(1, 255)
            name = colored.colors.names[idx].lower()
            color = Color(fg=name)
            self.image_hash_colors[hash] = color

        return color
