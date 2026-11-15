from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


PLAYER_Y = 113
PLAYER_WIDTH = 11
PLAYER_SPEED = 66.0
PLAYER_BULLET_SPEED = 92.0
ENEMY_BULLET_SPEED = 46.0
INVADER_WIDTH = 11
INVADER_HEIGHT = 7


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    WON = auto()


@dataclass
class Invader:
    x: float
    y: float
    row: int
    alive: bool = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), INVADER_WIDTH, INVADER_HEIGHT)


@dataclass
class Bullet:
    x: float
    y: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), 2, 4)


class SpaceInvaders:
    title = "INVADERS"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.stars = [(self.rng.randrange(WIDTH), self.rng.randrange(21, 108)) for _ in range(18)]
        self.reset()

    def reset(self) -> None:
        self.player_x = float((WIDTH - PLAYER_WIDTH) // 2)
        self.invaders = [
            Invader(10 + column * 21, 28 + row * 13, row)
            for row in range(3)
            for column in range(6)
        ]
        self.player_bullets: list[Bullet] = []
        self.enemy_bullets: list[Bullet] = []
        self.invader_direction = 1
        self.score = 0
        self.lives = 3
        self.fire_cooldown = 0.0
        self.enemy_fire_timer = self.rng.uniform(0.7, 1.3)
        self.status = Status.READY

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER, Status.WON}:
            if controls.just_pressed(Key.START) or controls.just_pressed(Key.A):
                if self.status is not Status.READY:
                    self.reset()
                self.status = Status.PLAYING
            return

        direction = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        self.player_x = max(2.0, min(WIDTH - PLAYER_WIDTH - 2.0, self.player_x + direction * PLAYER_SPEED * dt))

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0.0:
            self.player_bullets.append(Bullet(self.player_x + PLAYER_WIDTH / 2 - 1, PLAYER_Y - 4))
            self.fire_cooldown = 0.32

        self._move_invaders(dt)
        self._move_bullets(dt)
        self._enemy_fire(dt)
        self._resolve_collisions()

        if not any(invader.alive for invader in self.invaders):
            self.best = max(self.best, self.score)
            self.status = Status.WON
        elif any(invader.alive and invader.y + INVADER_HEIGHT >= PLAYER_Y for invader in self.invaders):
            self.best = max(self.best, self.score)
            self.status = Status.GAME_OVER

    def _move_invaders(self, dt: float) -> None:
        alive = [invader for invader in self.invaders if invader.alive]
        if not alive:
            return
        speed = 10.0 + (len(self.invaders) - len(alive)) * 0.7
        shift = self.invader_direction * speed * dt
        left = min(invader.x for invader in alive) + shift
        right = max(invader.x + INVADER_WIDTH for invader in alive) + shift
        if left <= 3 or right >= WIDTH - 3:
            self.invader_direction *= -1
            for invader in alive:
                invader.y += 5
        else:
            for invader in alive:
                invader.x += shift

    def _move_bullets(self, dt: float) -> None:
        for bullet in self.player_bullets:
            bullet.y -= PLAYER_BULLET_SPEED * dt
        for bullet in self.enemy_bullets:
            bullet.y += ENEMY_BULLET_SPEED * dt
        self.player_bullets = [bullet for bullet in self.player_bullets if bullet.y > 18]
        self.enemy_bullets = [bullet for bullet in self.enemy_bullets if bullet.y < HEIGHT]

    def _enemy_fire(self, dt: float) -> None:
        self.enemy_fire_timer -= dt
        if self.enemy_fire_timer > 0:
            return
        columns: dict[int, Invader] = {}
        for invader in self.invaders:
            if invader.alive:
                column = round((invader.x - 10) / 21)
                if column not in columns or invader.y > columns[column].y:
                    columns[column] = invader
        if columns:
            shooter = self.rng.choice(list(columns.values()))
            self.enemy_bullets.append(Bullet(shooter.x + INVADER_WIDTH / 2, shooter.y + INVADER_HEIGHT))
        self.enemy_fire_timer = self.rng.uniform(0.65, 1.25)

    def _resolve_collisions(self) -> None:
        for bullet in list(self.player_bullets):
            target = next((invader for invader in self.invaders if invader.alive and bullet.rect.colliderect(invader.rect)), None)
            if target is not None:
                target.alive = False
                self.score += (3 - target.row) * 10
                self.player_bullets.remove(bullet)

        player_rect = pygame.Rect(round(self.player_x), PLAYER_Y, PLAYER_WIDTH, 7)
        if any(bullet.rect.colliderect(player_rect) for bullet in self.enemy_bullets):
            self.enemy_bullets = [bullet for bullet in self.enemy_bullets if not bullet.rect.colliderect(player_rect)]
            self.lives -= 1
            if self.lives <= 0:
                self.best = max(self.best, self.score)
                self.status = Status.GAME_OVER

        for player_bullet in list(self.player_bullets):
            enemy_bullet = next(
                (bullet for bullet in self.enemy_bullets if player_bullet.rect.colliderect(bullet.rect)),
                None,
            )
            if enemy_bullet is not None:
                self.player_bullets.remove(player_bullet)
                self.enemy_bullets.remove(enemy_bullet)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"S {self.score:03d}", 3, 3, color=COLORS.accent, size=8, bold=True)
        text(surface, f"HI {self.best:03d}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"L {self.lives}", 102, 3, color=COLORS.food, size=8, bold=True)
        pygame.draw.line(surface, COLORS.accent_dark, (2, 17), (125, 17))

        for x, y in self.stars:
            surface.set_at((x, y), (35, 47, 58))
        for invader in self.invaders:
            if invader.alive:
                self._draw_invader(surface, invader)
        for bullet in self.player_bullets:
            pygame.draw.rect(surface, COLORS.food, bullet.rect)
        for bullet in self.enemy_bullets:
            pygame.draw.rect(surface, COLORS.danger, bullet.rect)

        px = round(self.player_x)
        pygame.draw.rect(surface, COLORS.accent, (px + 4, PLAYER_Y, 3, 2))
        pygame.draw.rect(surface, COLORS.accent, (px + 2, PLAYER_Y + 2, 7, 2))
        pygame.draw.rect(surface, COLORS.accent, (px, PLAYER_Y + 4, PLAYER_WIDTH, 3))
        pygame.draw.line(surface, COLORS.accent_dark, (2, 122), (125, 122))

        if self.status is Status.READY:
            self._overlay(surface, "INVADERS", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")
        elif self.status is Status.WON:
            self._overlay(surface, "ZWYCIESTWO", "A: JESZCZE RAZ")

    @staticmethod
    def _draw_invader(surface: pygame.Surface, invader: Invader) -> None:
        x, y = round(invader.x), round(invader.y)
        color = (86, 232 - invader.row * 25, 154 + invader.row * 28)
        pygame.draw.rect(surface, color, (x + 2, y, 7, 2))
        pygame.draw.rect(surface, color, (x, y + 2, 11, 3))
        pygame.draw.rect(surface, COLORS.background, (x + 2, y + 2, 2, 2))
        pygame.draw.rect(surface, COLORS.background, (x + 7, y + 2, 2, 2))
        pygame.draw.rect(surface, color, (x + 2, y + 5, 2, 2))
        pygame.draw.rect(surface, color, (x + 7, y + 5, 2, 2))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 50, 106, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 54, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 70, color=COLORS.food, size=7, center=True)
