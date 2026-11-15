from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


FIELD_TOP = 18
TANK_SIZE = 9
PLAYER_SPEED = 38.0
ENEMY_SPEED = 19.0
BULLET_SPEED = 72.0

DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    WON = auto()


@dataclass
class Wall:
    x: int
    y: int
    breakable: bool = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, 8, 8)


@dataclass
class Tank:
    x: float
    y: float
    direction: str = "up"
    move_timer: float = 0.0
    fire_timer: float = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), TANK_SIZE, TANK_SIZE)


@dataclass
class Bullet:
    x: float
    y: float
    dx: int
    dy: int
    friendly: bool

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), 3, 3)


class Tanks:
    title = "CZOLGI"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.player = Tank(59.0, 109.0)
        self.base_rect = pygame.Rect(60, 119, 8, 7)
        self.enemies = [
            Tank(8.0, 23.0, "down", fire_timer=0.7),
            Tank(59.0, 23.0, "down", fire_timer=1.2),
            Tank(110.0, 23.0, "down", fire_timer=1.7),
        ]
        self.walls = self._make_walls()
        self.bullets: list[Bullet] = []
        self.score = 0
        self.lives = 3
        self.fire_cooldown = 0.0
        self.invulnerable = 0.0
        self.status = Status.READY

    @staticmethod
    def _make_walls() -> list[Wall]:
        walls: list[Wall] = []
        # Krótkie murki zostawiają szerokie przejazdy na małym ekranie.
        for x, y in (
            (24, 35), (32, 35), (88, 35), (96, 35),
            (48, 51), (56, 51), (64, 51), (72, 51),
            (16, 67), (24, 67), (96, 67), (104, 67),
            (40, 83), (48, 83), (72, 83), (80, 83),
            (40, 99), (80, 99),
            (52, 115), (68, 115),
        ):
            walls.append(Wall(x, y, True))
        for x, y in ((0, 59), (120, 59), (0, 91), (120, 91)):
            walls.append(Wall(x, y, False))
        return walls

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER, Status.WON}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is not Status.READY:
                    self.reset()
                self.status = Status.PLAYING
            return

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self._move_player(dt, controls)
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0.0:
            self._fire(self.player, friendly=True)
            self.fire_cooldown = 0.38

        self._move_enemies(dt)
        self._move_bullets(dt)
        self._resolve_bullets()

        if not self.enemies and self.status is Status.PLAYING:
            self.best = max(self.best, self.score)
            self.status = Status.WON

    def _move_player(self, dt: float, controls: InputFrame) -> None:
        for key, direction in (
            (Key.UP, "up"), (Key.DOWN, "down"),
            (Key.LEFT, "left"), (Key.RIGHT, "right"),
        ):
            if controls.is_held(key):
                self.player.direction = direction
                dx, dy = DIRECTIONS[direction]
                self._try_move(self.player, dx * PLAYER_SPEED * dt, dy * PLAYER_SPEED * dt, self.enemies)
                break

    def _move_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            enemy.move_timer -= dt
            enemy.fire_timer -= dt
            if enemy.move_timer <= 0.0:
                # Częściej jadą w dół, więc stanowią zagrożenie dla bazy.
                enemy.direction = self.rng.choice(("down", "down", "left", "right", "up"))
                enemy.move_timer = self.rng.uniform(0.45, 1.15)
            dx, dy = DIRECTIONS[enemy.direction]
            others = [tank for tank in self.enemies if tank is not enemy] + [self.player]
            if not self._try_move(enemy, dx * ENEMY_SPEED * dt, dy * ENEMY_SPEED * dt, others):
                enemy.move_timer = 0.0
            if enemy.fire_timer <= 0.0:
                self._fire(enemy, friendly=False)
                enemy.fire_timer = self.rng.uniform(0.9, 1.7)

    def _try_move(self, tank: Tank, dx: float, dy: float, other_tanks: list[Tank]) -> bool:
        old_x, old_y = tank.x, tank.y
        tank.x = max(1.0, min(WIDTH - TANK_SIZE - 1.0, tank.x + dx))
        tank.y = max(float(FIELD_TOP + 2), min(HEIGHT - TANK_SIZE - 2.0, tank.y + dy))
        blocked = any(tank.rect.colliderect(wall.rect) for wall in self.walls)
        blocked = blocked or tank.rect.colliderect(self.base_rect)
        blocked = blocked or any(tank.rect.colliderect(other.rect) for other in other_tanks)
        if blocked:
            tank.x, tank.y = old_x, old_y
            return False
        return True

    def _fire(self, tank: Tank, friendly: bool) -> None:
        dx, dy = DIRECTIONS[tank.direction]
        x = tank.rect.centerx - 1 + dx * 6
        y = tank.rect.centery - 1 + dy * 6
        self.bullets.append(Bullet(float(x), float(y), dx, dy, friendly))

    def _move_bullets(self, dt: float) -> None:
        for bullet in self.bullets:
            bullet.x += bullet.dx * BULLET_SPEED * dt
            bullet.y += bullet.dy * BULLET_SPEED * dt
        self.bullets = [
            bullet for bullet in self.bullets
            if -3 < bullet.x < WIDTH and FIELD_TOP - 3 < bullet.y < HEIGHT
        ]

    def _resolve_bullets(self) -> None:
        for bullet in list(self.bullets):
            wall = next((wall for wall in self.walls if bullet.rect.colliderect(wall.rect)), None)
            if wall is not None:
                self.bullets.remove(bullet)
                if wall.breakable:
                    self.walls.remove(wall)
                continue

            if bullet.rect.colliderect(self.base_rect):
                self.bullets.remove(bullet)
                if not bullet.friendly:
                    self._finish_game()
                continue

            if bullet.friendly:
                enemy = next((tank for tank in self.enemies if bullet.rect.colliderect(tank.rect)), None)
                if enemy is not None:
                    self.enemies.remove(enemy)
                    self.bullets.remove(bullet)
                    self.score += 100
            elif self.invulnerable == 0.0 and bullet.rect.colliderect(self.player.rect):
                self.bullets.remove(bullet)
                self.lives -= 1
                if self.lives <= 0:
                    self._finish_game()
                else:
                    self.player.x, self.player.y = 59.0, 109.0
                    self.player.direction = "up"
                    self.invulnerable = 1.2

        # Przeciwne pociski mogą zderzyć się w locie.
        for friendly in [bullet for bullet in self.bullets if bullet.friendly]:
            enemy = next(
                (bullet for bullet in self.bullets if not bullet.friendly and friendly.rect.colliderect(bullet.rect)),
                None,
            )
            if enemy is not None and friendly in self.bullets:
                self.bullets.remove(friendly)
                self.bullets.remove(enemy)

    def _finish_game(self) -> None:
        self.best = max(self.best, self.score)
        self.status = Status.GAME_OVER

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((25, 43, 29))
        pygame.draw.rect(surface, COLORS.background, (0, 0, WIDTH, FIELD_TOP))
        text(surface, f"S {self.score:03d}", 3, 3, color=COLORS.accent, size=8, bold=True)
        text(surface, f"HI {self.best:03d}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"L {self.lives}", 103, 3, color=COLORS.food, size=8, bold=True)

        for wall in self.walls:
            self._draw_wall(surface, wall)
        self._draw_base(surface)
        for enemy in self.enemies:
            self._draw_tank(surface, enemy, COLORS.danger)
        if self.invulnerable == 0.0 or int(self.invulnerable * 10) % 2 == 0:
            self._draw_tank(surface, self.player, COLORS.food)
        for bullet in self.bullets:
            pygame.draw.rect(surface, COLORS.text if bullet.friendly else COLORS.danger, bullet.rect)

        if self.status is Status.READY:
            self._overlay(surface, "CZOLGI", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "BAZA STRACONA", "A: JESZCZE RAZ")
        elif self.status is Status.WON:
            self._overlay(surface, "ZWYCIESTWO", "A: JESZCZE RAZ")

    @staticmethod
    def _draw_wall(surface: pygame.Surface, wall: Wall) -> None:
        if wall.breakable:
            pygame.draw.rect(surface, (153, 76, 49), wall.rect)
            pygame.draw.line(surface, (224, 132, 73), wall.rect.topleft, wall.rect.topright)
            pygame.draw.line(surface, (77, 43, 34), (wall.x, wall.y + 4), (wall.x + 7, wall.y + 4))
            pygame.draw.line(surface, (77, 43, 34), (wall.x + 4, wall.y), (wall.x + 4, wall.y + 3))
        else:
            pygame.draw.rect(surface, (104, 117, 120), wall.rect)
            pygame.draw.rect(surface, (169, 181, 178), wall.rect, 1)

    @staticmethod
    def _draw_tank(surface: pygame.Surface, tank: Tank, color: tuple[int, int, int]) -> None:
        rect = tank.rect
        pygame.draw.rect(surface, color, (rect.x, rect.y + 1, 2, 7))
        pygame.draw.rect(surface, color, (rect.right - 2, rect.y + 1, 2, 7))
        pygame.draw.rect(surface, color, (rect.x + 2, rect.y + 2, 5, 5))
        pygame.draw.rect(surface, COLORS.background, (rect.x + 4, rect.y + 4, 1, 1))
        dx, dy = DIRECTIONS[tank.direction]
        pygame.draw.line(surface, color, rect.center, (rect.centerx + dx * 5, rect.centery + dy * 5), 2)

    def _draw_base(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COLORS.accent_dark, self.base_rect)
        pygame.draw.polygon(surface, COLORS.accent, ((64, 120), (61, 125), (67, 125)))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(8, 50, 112, 36)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 55, color=COLORS.text, size=10, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 72, color=COLORS.food, size=7, center=True)
