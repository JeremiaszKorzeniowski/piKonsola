from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


BOARD_WIDTH = 10
BOARD_HEIGHT = 20
CELL = 5
BOARD_X = 6
BOARD_Y = 24

SHAPES = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
}

PIECE_COLORS = {
    "I": (65, 211, 224),
    "J": (76, 110, 245),
    "L": (244, 156, 54),
    "O": (244, 211, 72),
    "S": (84, 201, 105),
    "T": (174, 91, 214),
    "Z": (234, 77, 84),
}

LINE_SCORES = (0, 100, 300, 500, 800)


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Piece:
    kind: str
    x: int = 3
    y: int = -2
    rotation: int = 0


class Tetris:
    title = "TETRIS"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.board: list[list[Optional[str]]] = [
            [None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)
        ]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.fall_timer = 0.0
        self.move_timer = 0.0
        self.held_direction = 0
        self.bag: list[str] = []
        self.active = Piece(self._take_from_bag())
        self.next_kind = self._take_from_bag()
        self.status = Status.READY

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
            return

        if controls.just_pressed(Key.UP) or controls.just_pressed(Key.A):
            self._rotate()
        if controls.just_pressed(Key.B):
            distance = 0
            while self._move(0, 1):
                distance += 1
            self.score += distance * 2
            self._lock_piece()
            return

        direction = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        if direction != self.held_direction:
            self.held_direction = direction
            self.move_timer = 0.0
            if direction:
                self._move(direction, 0)
        elif direction:
            self.move_timer += dt
            if self.move_timer >= 0.16:
                self.move_timer -= 0.07
                self._move(direction, 0)

        interval = self._fall_interval()
        self.fall_timer += dt * (10.0 if controls.is_held(Key.DOWN) else 1.0)
        while self.fall_timer >= interval and self.status is Status.PLAYING:
            self.fall_timer -= interval
            if not self._move(0, 1):
                self._lock_piece()
                break

    def _take_from_bag(self) -> str:
        if not self.bag:
            self.bag = list(SHAPES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def _cells(self, piece: Optional[Piece] = None) -> tuple[tuple[int, int], ...]:
        piece = piece or self.active
        cells = SHAPES[piece.kind]
        if piece.kind == "O":
            return tuple((piece.x + x, piece.y + y) for x, y in cells)
        rotated = cells
        for _ in range(piece.rotation % 4):
            rotated = tuple((3 - y, x) for x, y in rotated)
        return tuple((piece.x + x, piece.y + y) for x, y in rotated)

    def _valid(self, piece: Piece) -> bool:
        for x, y in self._cells(piece):
            if x < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def _move(self, dx: int, dy: int) -> bool:
        candidate = Piece(
            self.active.kind,
            self.active.x + dx,
            self.active.y + dy,
            self.active.rotation,
        )
        if not self._valid(candidate):
            return False
        self.active = candidate
        return True

    def _rotate(self) -> bool:
        if self.active.kind == "O":
            return True
        rotation = (self.active.rotation + 1) % 4
        # Proste wall-kicki wystarczają na wąskiej planszy i wybaczają obrót przy ścianie.
        for offset in (0, -1, 1, -2, 2):
            candidate = Piece(self.active.kind, self.active.x + offset, self.active.y, rotation)
            if self._valid(candidate):
                self.active = candidate
                return True
        return False

    def _lock_piece(self) -> None:
        cells = self._cells()
        if any(y < 0 for _, y in cells):
            self._finish_game()
            return
        for x, y in cells:
            self.board[y][x] = self.active.kind

        full_rows = [row for row in range(BOARD_HEIGHT) if all(self.board[row])]
        if full_rows:
            for row in reversed(full_rows):
                del self.board[row]
            for _ in full_rows:
                self.board.insert(0, [None for _ in range(BOARD_WIDTH)])
            count = len(full_rows)
            self.score += LINE_SCORES[count] * self.level
            self.lines += count
            self.level = 1 + self.lines // 10

        self.active = Piece(self.next_kind)
        self.next_kind = self._take_from_bag()
        self.fall_timer = 0.0
        if not self._valid(self.active):
            self._finish_game()

    def _finish_game(self) -> None:
        self.best = max(self.best, self.score)
        self.status = Status.GAME_OVER

    def _fall_interval(self) -> float:
        return max(0.08, 0.72 * (0.84 ** (self.level - 1)))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, "TETRIS", 4, 4, color=COLORS.accent, size=10, bold=True)
        text(surface, f"HI {self.best}", 92, 5, color=COLORS.muted, size=7)

        board_rect = pygame.Rect(BOARD_X - 1, BOARD_Y - 1, BOARD_WIDTH * CELL + 2, BOARD_HEIGHT * CELL + 2)
        pygame.draw.rect(surface, COLORS.panel, board_rect)
        pygame.draw.rect(surface, COLORS.accent_dark, board_rect, 1)

        for y, row in enumerate(self.board):
            for x, kind in enumerate(row):
                if kind is not None:
                    self._draw_block(surface, x, y, PIECE_COLORS[kind])

        if self.status is Status.PLAYING:
            ghost = Piece(self.active.kind, self.active.x, self.active.y, self.active.rotation)
            while self._valid(Piece(ghost.kind, ghost.x, ghost.y + 1, ghost.rotation)):
                ghost.y += 1
            for x, y in self._cells(ghost):
                if y >= 0:
                    rect = pygame.Rect(BOARD_X + x * CELL + 1, BOARD_Y + y * CELL + 1, CELL - 2, CELL - 2)
                    pygame.draw.rect(surface, COLORS.muted, rect, 1)
            for x, y in self._cells():
                if y >= 0:
                    self._draw_block(surface, x, y, PIECE_COLORS[self.active.kind])

        self._draw_sidebar(surface)
        if self.status is Status.READY:
            self._overlay(surface, "TETRIS", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC GRY", "A: JESZCZE RAZ")

    @staticmethod
    def _draw_block(surface: pygame.Surface, x: int, y: int, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(BOARD_X + x * CELL, BOARD_Y + y * CELL, CELL, CELL)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.line(surface, tuple(min(255, channel + 45) for channel in color), rect.topleft, rect.topright)
        pygame.draw.line(surface, tuple(max(0, channel - 55) for channel in color), rect.bottomleft, rect.bottomright)

    def _draw_sidebar(self, surface: pygame.Surface) -> None:
        x = 64
        text(surface, "WYNIK", x, 26, color=COLORS.muted, size=7)
        text(surface, str(self.score), x, 35, color=COLORS.text, size=9, bold=True)
        text(surface, "LINIE", x, 50, color=COLORS.muted, size=7)
        text(surface, str(self.lines), x, 59, color=COLORS.food, size=9, bold=True)
        text(surface, "POZIOM", x, 74, color=COLORS.muted, size=7)
        text(surface, str(self.level), x, 83, color=COLORS.accent, size=9, bold=True)
        text(surface, "DALEJ", x, 98, color=COLORS.muted, size=7)
        color = PIECE_COLORS[self.next_kind]
        for block_x, block_y in SHAPES[self.next_kind]:
            rect = pygame.Rect(x + block_x * 5, 108 + block_y * 5, 4, 4)
            pygame.draw.rect(surface, color, rect)

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(12, 50, 104, 36)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 55, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 73, color=COLORS.food, size=7, center=True)
