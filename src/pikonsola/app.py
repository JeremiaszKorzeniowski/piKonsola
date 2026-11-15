from __future__ import annotations

import os
import subprocess
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import pygame

from .config import COLORS, FPS, HEIGHT, WIDTH
from .display import create_display, selected_display
from .games.arkanoid import Arkanoid
from .games.asteroids import Asteroids
from .games.defender import Defender
from .games.nibbles import Nibbles
from .games.pacman import Pacman
from .games.platformer import Platformer
from .games.river import River
from .games.snow_arena import SnowArena
from .games.sokoban import Sokoban
from .games.space_invaders import SpaceInvaders
from .games.tanks import Tanks
from .games.tetris import Tetris
from .input import InputBackend, Key, create_input
from .ui import frame, text


LAUNCHER_VISIBLE_GAMES = 4


class Screen(Enum):
    LAUNCHER = auto()
    GAME = auto()
    POWER = auto()
    UPDATE_CONFIRM = auto()
    UPDATING = auto()
    UPDATE_RESULT = auto()


class ConsoleApp:
    def __init__(self, controls: InputBackend) -> None:
        self.controls = controls
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.screen = Screen.LAUNCHER
        self.game = Nibbles()
        self.running = True
        self.restart_requested = False
        self.selected = 0
        self.power_selected = 0
        self.games = [
            ("SOKOBAN", Sokoban()),
            ("PLATFUS", Platformer()),
            ("SNIEZKA 3D", SnowArena()),
            ("NIBBLES", self.game),
            ("INVADERS", SpaceInvaders()),
            ("ASTEROIDS", Asteroids()),
            ("DEFENDER", Defender()),
            ("PAC-MAN", Pacman()),
            ("RIVER", River()),
            ("CZOLGI", Tanks()),
            ("TETRIS", Tetris()),
            ("ARKANOID", Arkanoid()),
        ]
        self.update_process: Optional[subprocess.Popen] = None
        self.update_elapsed = 0.0
        self.update_ok = False
        self.update_output = ""

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
            elif controls.just_pressed(Key.UP):
                self.power_selected = (self.power_selected - 1) % 3
            elif controls.just_pressed(Key.DOWN):
                self.power_selected = (self.power_selected + 1) % 3
            elif controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.power_selected == 2:
                    self.screen = Screen.LAUNCHER
                else:
                    self.running = False
                    if os.getenv("PIKONSOLA_ALLOW_POWEROFF") == "1":
                        command = "/usr/sbin/poweroff" if self.power_selected == 0 else "/usr/sbin/reboot"
                        subprocess.Popen(["sudo", "-n", command])
            return

        if self.screen is Screen.UPDATE_CONFIRM:
            if controls.just_pressed(Key.B) or controls.just_pressed(Key.MENU):
                self.screen = Screen.LAUNCHER
            elif controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                self._start_update()
            return

        if self.screen is Screen.UPDATING:
            self.update_elapsed += dt
            self._poll_update()
            return

        if self.screen is Screen.UPDATE_RESULT:
            self.update_elapsed += dt
            if self.update_ok and self.update_elapsed >= 1.5:
                self.restart_requested = True
                self.running = False
            elif not self.update_ok and (
                controls.just_pressed(Key.A)
                or controls.just_pressed(Key.B)
                or controls.just_pressed(Key.MENU)
            ):
                self.screen = Screen.LAUNCHER
            return

        if controls.just_pressed(Key.UP):
            self.selected = (self.selected - 1) % len(self.games)
        if controls.just_pressed(Key.DOWN):
            self.selected = (self.selected + 1) % len(self.games)
        if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
            self.game = self.games[self.selected][1]
            self.screen = Screen.GAME
        elif controls.just_pressed(Key.B):
            self.screen = Screen.UPDATE_CONFIRM
        elif controls.just_pressed(Key.MENU):
            self.power_selected = 0
            self.screen = Screen.POWER

    def _start_update(self) -> None:
        project_dir = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        self.update_elapsed = 0.0
        self.update_output = ""
        try:
            self.update_process = subprocess.Popen(
                ["git", "pull", "--ff-only", "origin", "main"],
                cwd=str(project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        except OSError as exc:
            self.update_ok = False
            self.update_output = str(exc)
            print(f"Aktualizacja nie wystartowała: {exc}", flush=True)
            self.screen = Screen.UPDATE_RESULT
            return
        self.screen = Screen.UPDATING

    def _poll_update(self) -> None:
        if self.update_process is None or self.update_process.poll() is None:
            return
        output, _ = self.update_process.communicate()
        self.update_output = output.strip()
        self.update_ok = self.update_process.returncode == 0
        if self.update_output:
            print(self.update_output, flush=True)
        self.update_elapsed = 0.0
        self.screen = Screen.UPDATE_RESULT

    def draw(self) -> pygame.Surface:
        if self.screen is Screen.GAME:
            self.game.draw(self.canvas)
        elif self.screen is Screen.POWER:
            self._draw_power()
        elif self.screen is Screen.UPDATE_CONFIRM:
            self._draw_update_confirm()
        elif self.screen is Screen.UPDATING:
            self._draw_updating()
        elif self.screen is Screen.UPDATE_RESULT:
            self._draw_update_result()
        else:
            self._draw_launcher()
        return self.canvas

    def _draw_launcher(self) -> None:
        frame(self.canvas, "piKONSOLA", title_size=11)
        text(self.canvas, "GRY", 8, 23, color=COLORS.muted, size=8)
        first = self._launcher_window_start()
        visible_games = self.games[first : first + LAUNCHER_VISIBLE_GAMES]
        for row, (name, _) in enumerate(visible_games):
            index = first + row
            y = 31 + row * 16
            selected = index == self.selected
            if selected:
                pygame.draw.rect(self.canvas, COLORS.accent_dark, (7, y - 1, 114, 15))
                text(self.canvas, ">", 11, y, color=COLORS.food, size=12, bold=True)
            text(self.canvas, name, 23, y, size=12 if selected else 11, bold=selected)
        if first > 0:
            pygame.draw.polygon(self.canvas, COLORS.muted, ((115, 27), (119, 27), (117, 23)))
        if first + LAUNCHER_VISIBLE_GAMES < len(self.games):
            pygame.draw.polygon(self.canvas, COLORS.muted, ((115, 91), (119, 91), (117, 95)))
        text(self.canvas, "KEY2: AKTUALIZACJA", 7, 97, color=COLORS.food, size=8)
        text(self.canvas, "A: GRAJ", 7, 106, color=COLORS.accent, size=9)
        text(self.canvas, "MENU: OFF", 69, 106, color=COLORS.muted, size=9)

    def _launcher_window_start(self) -> int:
        """Keep the selected game visible without compressing the menu rows."""
        return max(
            0,
            min(
                self.selected - LAUNCHER_VISIBLE_GAMES + 1,
                len(self.games) - LAUNCHER_VISIBLE_GAMES,
            ),
        )

    def _draw_power(self) -> None:
        frame(self.canvas, "ZASILANIE")
        options = ("WYLACZ", "RESTART", "POWROT")
        for index, label in enumerate(options):
            y = 31 + index * 22
            if index == self.power_selected:
                pygame.draw.rect(self.canvas, COLORS.accent_dark, (17, y - 3, 94, 17))
                text(self.canvas, ">", 22, y, color=COLORS.food, size=9, bold=True)
            color = COLORS.danger if index < 2 else COLORS.accent
            text(self.canvas, label, WIDTH // 2, y, color=color, size=10, center=True, bold=index == self.power_selected)
        text(self.canvas, "A: OK  B: POWROT", WIDTH // 2, 105, color=COLORS.muted, size=7, center=True)

    def _draw_update_confirm(self) -> None:
        frame(self.canvas, "AKTUALIZACJA")
        text(self.canvas, "POBRAC NOWA", WIDTH // 2, 36, size=11, center=True, bold=True)
        text(self.canvas, "WERSJE?", WIDTH // 2, 52, size=11, center=True, bold=True)
        text(self.canvas, "KEY1: TAK", 10, 87, color=COLORS.accent, size=8, bold=True)
        text(self.canvas, "KEY2: NIE", 69, 87, color=COLORS.muted, size=8)

    def _draw_updating(self) -> None:
        frame(self.canvas, "AKTUALIZACJA")
        dots = "." * (1 + int(self.update_elapsed * 3) % 3)
        text(self.canvas, "POBIERANIE", WIDTH // 2, 43, size=11, center=True, bold=True)
        text(self.canvas, dots, WIDTH // 2, 62, color=COLORS.food, size=12, center=True)
        text(self.canvas, "NIE WYLACZAJ", WIDTH // 2, 91, color=COLORS.muted, size=8, center=True)

    def _draw_update_result(self) -> None:
        frame(self.canvas, "AKTUALIZACJA")
        if self.update_ok:
            text(self.canvas, "GOTOWE", WIDTH // 2, 42, color=COLORS.accent, size=14, center=True, bold=True)
            text(self.canvas, "RESTART...", WIDTH // 2, 68, color=COLORS.text, size=9, center=True)
        else:
            text(self.canvas, "BLAD", WIDTH // 2, 39, color=COLORS.danger, size=14, center=True, bold=True)
            text(self.canvas, "SPRAWDZ SSH", WIDTH // 2, 63, color=COLORS.text, size=8, center=True)
            text(self.canvas, "KEY2: POWROT", WIDTH // 2, 91, color=COLORS.muted, size=7, center=True)


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
    if app.restart_requested:
        os.execv(sys.executable, [sys.executable, "-m", "pikonsola"])

