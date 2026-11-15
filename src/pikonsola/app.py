from __future__ import annotations

import os
import subprocess
from enum import Enum, auto

import pygame

from .config import COLORS, FPS, HEIGHT, WIDTH
from .display import create_display, selected_display
from .games.nibbles import Nibbles
from .input import InputBackend, Key, create_input
from .ui import frame, text


class Screen(Enum):
    LAUNCHER = auto()
    GAME = auto()
    POWER = auto()


class ConsoleApp:
    def __init__(self, controls: InputBackend) -> None:
        self.controls = controls
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.screen = Screen.LAUNCHER
        self.game = Nibbles()
        self.running = True
        self.selected = 0
        self.games = [("NIBBLES", self.game)]

    def update(self, dt: float) -> None:
        controls = self.controls.poll()
        if self.screen is Screen.GAME:
            if controls.menu_held_seconds >= 1.5:
                self.screen = Screen.LAUNCHER
            else:
                self.game.update(dt, controls)
            return

        if self.screen is Screen.POWER:
            if controls.just_pressed(Key.B) or controls.just_pressed(Key.MENU):
                self.screen = Screen.LAUNCHER
            elif controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                self.running = False
                if os.getenv("PIKONSOLA_ALLOW_POWEROFF") == "1":
                    subprocess.Popen(["sudo", "/usr/sbin/poweroff"])
            return

        if controls.just_pressed(Key.UP):
            self.selected = (self.selected - 1) % len(self.games)
        if controls.just_pressed(Key.DOWN):
            self.selected = (self.selected + 1) % len(self.games)
        if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
            self.screen = Screen.GAME
        elif controls.just_pressed(Key.MENU):
            self.screen = Screen.POWER

    def draw(self) -> pygame.Surface:
        if self.screen is Screen.GAME:
            self.game.draw(self.canvas)
        elif self.screen is Screen.POWER:
            self._draw_power()
        else:
            self._draw_launcher()
        return self.canvas

    def _draw_launcher(self) -> None:
        frame(self.canvas, "piKONSOLA")
        text(self.canvas, "GRY", 8, 25, color=COLORS.muted, size=8)
        for index, (name, _) in enumerate(self.games):
            y = 38 + index * 18
            if index == self.selected:
                pygame.draw.rect(self.canvas, COLORS.accent_dark, (7, y - 2, 114, 16))
                text(self.canvas, ">", 11, y, color=COLORS.food, size=9, bold=True)
            text(self.canvas, name, 23, y, size=9, bold=index == self.selected)
        text(self.canvas, "A: GRAJ", 7, 106, color=COLORS.accent, size=8)
        text(self.canvas, "MENU: OFF", 69, 106, color=COLORS.muted, size=7)

    def _draw_power(self) -> None:
        frame(self.canvas, "ZASILANIE")
        text(self.canvas, "WYLACZYC", WIDTH // 2, 37, size=12, center=True, bold=True)
        text(self.canvas, "KONSOLE?", WIDTH // 2, 53, size=12, center=True, bold=True)
        text(self.canvas, "A: TAK", 15, 87, color=COLORS.danger, size=9, bold=True)
        text(self.canvas, "B: NIE", 71, 87, color=COLORS.accent, size=9, bold=True)


def main() -> None:
    display_kind = selected_display()
    if display_kind == "spi":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    output = create_display(display_kind)
    controls = create_input()
    app = ConsoleApp(controls)
    clock = pygame.time.Clock()
    try:
        while app.running:
            dt = min(clock.tick(FPS) / 1000.0, 0.1)
            app.update(dt)
            output.present(app.draw())
    finally:
        controls.close()
        output.close()
        pygame.quit()

