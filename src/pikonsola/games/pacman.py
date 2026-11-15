from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, WIDTH
from ..input import InputFrame, Key
from ..ui import text


CELL = 7
ORIGIN_X = 11
ORIGIN_Y = 24
PLAYER_STEP = 0.13
GHOST_STEP = 0.32

MAZE = (
    "###############",
    "#......#......#",
    "#.###..#..###.#",
    "#.............#",
    "#.##.#####.##.#",
    "#....#...#....#",
    ".....#...#.....",
    "#.##.#...#.##.#",
    "#....##.##....#",
    "#.##.......##.#",
    "#.###.###.###.#",
    "#......#......#",
    "###############",
)

ROWS = len(MAZE)
COLS = len(MAZE[0])
FLOOR = {(x, y) for y, row in enumerate(MAZE) for x, cell in enumerate(row) if cell != "#"}
DIRECTIONS = {
    Key.UP: (0, -1),
    Key.DOWN: (0, 1),
    Key.LEFT: (-1, 0),
    Key.RIGHT: (1, 0),
}


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    WON = auto()


@dataclass
class Ghost:
    position: tuple[int, int]
    spawn: tuple[int, int]
    direction: tuple[int, int]
    color: tuple[int, int, int]


class Pacman:
    title = "PAC-MAN"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.player = (7, 9)
        self.direction = (0, 0)
        self.next_direction = (0, 0)
        ghost_data = [
            ((6, 3), COLORS.danger),
            ((7, 3), (255, 142, 205)),
            ((8, 3), (80, 220, 235)),
        ]
        self.ghosts = [Ghost(position, position, (0, 1), color) for position, color in ghost_data]
        occupied = {self.player, *(ghost.position for ghost in self.ghosts)}
        self.pellets = FLOOR - occupied
        self.power_pellets = {(1, 1), (13, 1), (1, 11), (13, 11)} & self.pellets
        self.score = 0
        self.lives = 3
        self.player_elapsed = 0.0
        self.ghost_elapsed = 0.0
        self.frightened = 0.0
        self.status = Status.READY

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER, Status.WON}:
            if controls.just_pressed(Key.START) or controls.just_pressed(Key.A):
                if self.status is not Status.READY:
                    self.reset()
                self.status = Status.PLAYING
            return

        for key, direction in DIRECTIONS.items():
            if controls.just_pressed(key) or controls.is_held(key):
                self.next_direction = direction
                break

        self.frightened = max(0.0, self.frightened - dt)
        self.player_elapsed += dt
        self.ghost_elapsed += dt

        while self.player_elapsed >= PLAYER_STEP and self.status is Status.PLAYING:
            self.player_elapsed -= PLAYER_STEP
            self._move_player()
            self._resolve_collisions()

        while self.ghost_elapsed >= GHOST_STEP and self.status is Status.PLAYING:
            self.ghost_elapsed -= GHOST_STEP
            self._move_ghosts()
            self._resolve_collisions()

        if not self.pellets and self.status is Status.PLAYING:
            self.best = max(self.best, self.score)
            self.status = Status.WON

    def _move_player(self) -> None:
        if self._next_position(self.player, self.next_direction) in FLOOR:
            self.direction = self.next_direction
        destination = self._next_position(self.player, self.direction)
        if destination in FLOOR:
            self.player = destination
        if self.player in self.pellets:
            self.pellets.remove(self.player)
            self.score += 10
            if self.player in self.power_pellets:
                self.power_pellets.remove(self.player)
                self.frightened = 7.0

    def _move_ghosts(self) -> None:
        for ghost in self.ghosts:
            options = [
                direction
                for direction in DIRECTIONS.values()
                if self._next_position(ghost.position, direction) in FLOOR
            ]
            reverse = (-ghost.direction[0], -ghost.direction[1])
            if len(options) > 1 and reverse in options:
                options.remove(reverse)
            if not options:
                continue
            scored = [
                (self._distance(self._next_position(ghost.position, direction), self.player), direction)
                for direction in options
            ]
            if self.frightened > 0:
                best_distance = max(distance for distance, _ in scored)
            elif self.rng.random() < 0.75:
                best_distance = min(distance for distance, _ in scored)
            else:
                ghost.direction = self.rng.choice(options)
                ghost.position = self._next_position(ghost.position, ghost.direction)
                continue
            best = [direction for distance, direction in scored if distance == best_distance]
            ghost.direction = self.rng.choice(best)
            ghost.position = self._next_position(ghost.position, ghost.direction)

    def _resolve_collisions(self) -> None:
        for ghost in self.ghosts:
            if ghost.position != self.player:
                continue
            if self.frightened > 0:
                self.score += 200
                ghost.position = ghost.spawn
                ghost.direction = (0, 1)
            else:
                self.lives -= 1
                if self.lives <= 0:
                    self.best = max(self.best, self.score)
                    self.status = Status.GAME_OVER
                else:
                    self._reset_positions()
                return

    def _reset_positions(self) -> None:
        self.player = (7, 9)
        self.direction = (0, 0)
        self.next_direction = (0, 0)
        for ghost in self.ghosts:
            ghost.position = ghost.spawn
            ghost.direction = (0, 1)
        self.player_elapsed = 0.0
        self.ghost_elapsed = 0.0

    @staticmethod
    def _next_position(position: tuple[int, int], direction: tuple[int, int]) -> tuple[int, int]:
        x, y = position
        dx, dy = direction
        return ((x + dx) % COLS, y + dy)

    @staticmethod
    def _distance(first: tuple[int, int], second: tuple[int, int]) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"S {self.score:04d}", 3, 3, color=COLORS.food, size=7, bold=True)
        text(surface, f"HI {self.best:04d}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"L {self.lives}", 104, 3, color=COLORS.accent, size=7, bold=True)

        for y, row in enumerate(MAZE):
            for x, cell in enumerate(row):
                px, py = ORIGIN_X + x * CELL, ORIGIN_Y + y * CELL
                if cell == "#":
                    pygame.draw.rect(surface, (36, 76, 195), (px, py, CELL, CELL), 1)
                elif (x, y) in self.pellets:
                    radius = 2 if (x, y) in self.power_pellets else 1
                    pygame.draw.circle(surface, COLORS.food, (px + 3, py + 3), radius)

        self._draw_pacman(surface)
        for ghost in self.ghosts:
            self._draw_ghost(surface, ghost)

        if self.status is Status.READY:
            self._overlay(surface, "PAC-MAN", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")
        elif self.status is Status.WON:
            self._overlay(surface, "LABIRYNT CZYSTY", "A: JESZCZE RAZ")

    def _draw_pacman(self, surface: pygame.Surface) -> None:
        x = ORIGIN_X + self.player[0] * CELL + 3
        y = ORIGIN_Y + self.player[1] * CELL + 3
        pygame.draw.circle(surface, (255, 220, 45), (x, y), 3)
        if self.direction != (0, 0):
            dx, dy = self.direction
            pygame.draw.polygon(surface, COLORS.background, [(x, y), (x + dx * 4 - dy * 2, y + dy * 4 + dx * 2), (x + dx * 4 + dy * 2, y + dy * 4 - dx * 2)])

    def _draw_ghost(self, surface: pygame.Surface, ghost: Ghost) -> None:
        px = ORIGIN_X + ghost.position[0] * CELL
        py = ORIGIN_Y + ghost.position[1] * CELL
        color = (55, 75, 210) if self.frightened > 0 else ghost.color
        pygame.draw.circle(surface, color, (px + 3, py + 3), 3)
        pygame.draw.rect(surface, color, (px, py + 3, 7, 3))
        pygame.draw.rect(surface, COLORS.text, (px + 1, py + 2, 2, 2))
        pygame.draw.rect(surface, COLORS.text, (px + 4, py + 2, 2, 2))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(9, 52, 110, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 56, color=COLORS.text, size=10, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 71, color=COLORS.food, size=7, center=True)
