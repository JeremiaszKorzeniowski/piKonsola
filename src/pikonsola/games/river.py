from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


RIVER_TOP = 18
MIN_RIVER_WIDTH = 64
MAX_RIVER_WIDTH = 104
SECTION_HEIGHT = 12
PLAYER_WIDTH = 11
PLAYER_HEIGHT = 9
PLAYER_SPEED = 46.0
SCROLL_SPEED = 24.0
BULLET_SPEED = 72.0
FUEL_BURN_RATE = 1.8
BRIDGE_SPACING = 330

# Gotowe, lekkie warianty zmiany brzegu: przesunięcie środka i zmiana szerokości.
BANK_CHANGES = (
    (-5, -4), (-4, 2), (-3, 6), (-2, -6), (-1, 4),
    (0, -7), (0, 7), (1, -4), (2, 6), (3, -6), (4, 2), (5, 4),
)
OBJECT_KINDS = ("rock", "rock", "rock", "rock", "boat", "boat", "boat", "boat", "fuel")
SPAWN_JITTER = (0.0, 0.12, 0.24, 0.36)


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class RiverObject:
    x: float
    y: float
    kind: str

    @property
    def rect(self) -> pygame.Rect:
        sizes = {"rock": (9, 7), "boat": (9, 11), "fuel": (7, 9)}
        width, height = sizes[self.kind]
        return pygame.Rect(round(self.x), round(self.y), width, height)


@dataclass
class Bullet:
    x: float
    y: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), 2, 5)


@dataclass
class RiverSection:
    y: float
    left: float
    right: float


@dataclass
class Bridge:
    y: float


class River:
    title = "RIVER"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.player_x = float((WIDTH - PLAYER_WIDTH) // 2)
        self.player_y = 105.0
        self.objects: list[RiverObject] = []
        self.bullets: list[Bullet] = []
        self.bridges: list[Bridge] = []
        self.score = 0
        self.lives = 3
        self.fuel = 100.0
        self.stage = 0
        self.distance = 0.0
        self.next_bridge_distance = 260.0
        self.sections = self._initial_sections()
        self.spawn_timer = 0.65
        self.fire_cooldown = 0.0
        self.invulnerable = 0.0
        self.game_over_reason = "KONIEC"
        self.status = Status.READY

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
            return

        horizontal = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        vertical = int(controls.is_held(Key.DOWN)) - int(controls.is_held(Key.UP))
        self.player_x += horizontal * PLAYER_SPEED * dt
        self.player_y += vertical * PLAYER_SPEED * dt
        self.player_x = max(1.0, min(WIDTH - PLAYER_WIDTH - 1.0, self.player_x))
        self.player_y = max(42.0, min(HEIGHT - PLAYER_HEIGHT - 4.0, self.player_y))

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.fuel = max(0.0, self.fuel - FUEL_BURN_RATE * dt)
        if self.fuel == 0.0:
            self._finish_game("BRAK PALIWA")
            return
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0.0:
            self.bullets.append(Bullet(self.player_x + 4.5, self.player_y - 5))
            self.fire_cooldown = 0.38

        self.distance += SCROLL_SPEED * dt
        self._move_river(dt)
        self._move_objects(dt)
        self._spawn_objects(dt)
        self._spawn_bridge()
        self._resolve_collisions()

    def _initial_sections(self) -> list[RiverSection]:
        sections = [RiverSection(float(RIVER_TOP), 19.0, 109.0)]
        for y in range(RIVER_TOP + SECTION_HEIGHT, HEIGHT + SECTION_HEIGHT + 1, SECTION_HEIGHT):
            left, right = self._next_bounds(sections[-1].left, sections[-1].right)
            sections.append(RiverSection(float(y), left, right))
        return sections

    def _next_bounds(self, left: float, right: float) -> tuple[float, float]:
        center_change, width_change = self.rng.choice(BANK_CHANGES)
        width = max(MIN_RIVER_WIDTH, min(MAX_RIVER_WIDTH, right - left + width_change))
        center = (left + right) / 2 + center_change
        center = max(width / 2 + 3, min(WIDTH - width / 2 - 3, center))
        return center - width / 2, center + width / 2

    def _move_river(self, dt: float) -> None:
        shift = SCROLL_SPEED * dt
        for section in self.sections:
            section.y += shift
        while self.sections[0].y > RIVER_TOP:
            first = self.sections[0]
            left, right = self._next_bounds(first.left, first.right)
            self.sections.insert(0, RiverSection(first.y - SECTION_HEIGHT, left, right))
        self.sections = [section for section in self.sections if section.y <= HEIGHT + SECTION_HEIGHT]

    def _river_bounds(self, y: float) -> tuple[float, float]:
        if y <= self.sections[0].y:
            return self.sections[0].left, self.sections[0].right
        for upper, lower in zip(self.sections, self.sections[1:]):
            if y <= lower.y:
                span = lower.y - upper.y
                progress = 0.0 if span == 0 else (y - upper.y) / span
                left = upper.left + (lower.left - upper.left) * progress
                right = upper.right + (lower.right - upper.right) * progress
                return left, right
        return self.sections[-1].left, self.sections[-1].right

    def _stripe_rows(self) -> range:
        offset = int(self.distance) % 24
        return range(-24 + offset, HEIGHT, 24)

    def _move_objects(self, dt: float) -> None:
        for obj in self.objects:
            obj.y += SCROLL_SPEED * dt
        for bridge in self.bridges:
            bridge.y += SCROLL_SPEED * dt
        for bullet in self.bullets:
            bullet.y -= BULLET_SPEED * dt
        self.objects = [obj for obj in self.objects if obj.y < HEIGHT + 12]
        passed_bridges = [bridge for bridge in self.bridges if bridge.y >= HEIGHT]
        self.stage += len(passed_bridges)
        self.bridges = [bridge for bridge in self.bridges if bridge.y < HEIGHT]
        self.bullets = [bullet for bullet in self.bullets if bullet.y > RIVER_TOP - 1]

    def _spawn_objects(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        kind = self.rng.choice(OBJECT_KINDS)
        width = {"rock": 9, "boat": 9, "fuel": 7}[kind]
        left, right = self._river_bounds(RIVER_TOP + 1)
        x = self.rng.randint(round(left + 8), round(right - width - 8))
        self.objects.append(RiverObject(float(x), float(RIVER_TOP + 1), kind))
        self.spawn_timer = self._spawn_interval() + self.rng.choice(SPAWN_JITTER)

    def _spawn_interval(self) -> float:
        return max(0.65, 1.35 - self.stage * 0.11)

    def _spawn_bridge(self) -> None:
        if self.distance < self.next_bridge_distance:
            return
        self.bridges.append(Bridge(float(RIVER_TOP + 2)))
        self.next_bridge_distance += BRIDGE_SPACING

    def _bridge_rect(self, bridge: Bridge) -> pygame.Rect:
        left, right = self._river_bounds(bridge.y + 3)
        return pygame.Rect(round(left), round(bridge.y), max(1, round(right - left)), 6)

    def _resolve_collisions(self) -> None:
        for bullet in list(self.bullets):
            bridge = next(
                (candidate for candidate in self.bridges if bullet.rect.colliderect(self._bridge_rect(candidate))),
                None,
            )
            if bridge is not None:
                self.bullets.remove(bullet)
                self.bridges.remove(bridge)
                self.stage += 1
                self.score += 50
                continue
            target = next(
                (obj for obj in self.objects if obj.kind != "fuel" and bullet.rect.colliderect(obj.rect)),
                None,
            )
            if target is not None:
                self.objects.remove(target)
                self.bullets.remove(bullet)
                self.score += 10 if target.kind == "rock" else 20

        player_rect = pygame.Rect(round(self.player_x), round(self.player_y), PLAYER_WIDTH, PLAYER_HEIGHT)
        if self._player_on_bank(player_rect) and self.invulnerable == 0.0:
            self._hit_player()
            return

        fuel = next(
            (obj for obj in self.objects if obj.kind == "fuel" and obj.rect.colliderect(player_rect)),
            None,
        )
        if fuel is not None:
            self.objects.remove(fuel)
            self.fuel = min(100.0, self.fuel + 35.0)
            self.score += 25

        bridge = next(
            (candidate for candidate in self.bridges if self._bridge_rect(candidate).colliderect(player_rect)),
            None,
        )
        if bridge is not None and self.invulnerable == 0.0:
            self.bridges.remove(bridge)
            self.stage += 1
            self._hit_player()
            return

        obstacle = next(
            (obj for obj in self.objects if obj.kind != "fuel" and obj.rect.colliderect(player_rect)),
            None,
        )
        if obstacle is not None and self.invulnerable == 0.0:
            self.objects.remove(obstacle)
            self._hit_player()

    def _player_on_bank(self, player_rect: pygame.Rect) -> bool:
        for y in (player_rect.top, player_rect.centery, player_rect.bottom):
            left, right = self._river_bounds(y)
            if player_rect.left < left + 2 or player_rect.right > right - 2:
                return True
        return False

    def _hit_player(self) -> None:
        self.lives -= 1
        self.invulnerable = 1.0
        left, right = self._river_bounds(self.player_y + PLAYER_HEIGHT / 2)
        self.player_x = (left + right - PLAYER_WIDTH) / 2
        if self.lives <= 0:
            self._finish_game("KONIEC")

    def _finish_game(self, reason: str) -> None:
        self.best = max(self.best, self.score)
        self.game_over_reason = reason
        self.status = Status.GAME_OVER

    def draw(self, surface: pygame.Surface) -> None:
        bank = (45, 91, 55)
        water = (21, 78, 112)
        foam = (72, 144, 166)
        surface.fill(bank)
        left_bank = [(round(section.left), round(section.y)) for section in self.sections]
        right_bank = [(round(section.right), round(section.y)) for section in self.sections]
        pygame.draw.polygon(surface, water, left_bank + list(reversed(right_bank)))
        pygame.draw.lines(surface, (99, 145, 76), False, left_bank, 2)
        pygame.draw.lines(surface, (99, 145, 76), False, right_bank, 2)

        for y in self._stripe_rows():
            left, right = self._river_bounds(y)
            river_width = right - left
            x1 = round(left + river_width * 0.28)
            x2 = round(left + river_width * 0.72)
            pygame.draw.line(surface, foam, (x1, y), (x1, y + 6))
            pygame.draw.line(surface, foam, (x2, y + 8), (x2, y + 14))

        pygame.draw.rect(surface, COLORS.background, (0, 0, WIDTH, 18))
        text(surface, f"S {self.score:03d}", 3, 3, color=COLORS.accent, size=8, bold=True)
        text(surface, "F", 45, 3, color=COLORS.muted, size=8, bold=True)
        pygame.draw.rect(surface, COLORS.muted, (54, 5, 34, 7), 1)
        fuel_color = COLORS.accent if self.fuel > 30 else COLORS.danger
        pygame.draw.rect(surface, fuel_color, (56, 7, round(30 * self.fuel / 100), 3))
        text(surface, f"L {self.lives}", 103, 3, color=COLORS.food, size=8, bold=True)

        for obj in self.objects:
            self._draw_object(surface, obj)
        for bridge in self.bridges:
            self._draw_bridge(surface, bridge)
        for bullet in self.bullets:
            pygame.draw.rect(surface, COLORS.food, bullet.rect)
        if self.invulnerable == 0.0 or int(self.invulnerable * 10) % 2 == 0:
            self._draw_player(surface)

        if self.status is Status.READY:
            self._overlay(surface, "RIVER", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, self.game_over_reason, "A: JESZCZE RAZ")

    def _draw_player(self, surface: pygame.Surface) -> None:
        x, y = round(self.player_x), round(self.player_y)
        pygame.draw.rect(surface, COLORS.food, (x + 4, y, 3, 9))
        pygame.draw.rect(surface, COLORS.food, (x, y + 4, PLAYER_WIDTH, 3))
        pygame.draw.rect(surface, COLORS.text, (x + 4, y + 1, 3, 2))

    def _draw_bridge(self, surface: pygame.Surface, bridge: Bridge) -> None:
        rect = self._bridge_rect(bridge)
        pygame.draw.rect(surface, (132, 83, 47), rect)
        pygame.draw.line(surface, (224, 171, 93), rect.topleft, rect.topright)
        pygame.draw.line(surface, (83, 48, 31), rect.bottomleft, rect.bottomright)
        for x in range(rect.left + 4, rect.right, 8):
            pygame.draw.line(surface, (83, 48, 31), (x, rect.top), (x, rect.bottom - 1))

    @staticmethod
    def _draw_object(surface: pygame.Surface, obj: RiverObject) -> None:
        x, y = round(obj.x), round(obj.y)
        if obj.kind == "rock":
            pygame.draw.polygon(surface, (116, 121, 121), [(x + 1, y + 6), (x + 2, y + 1), (x + 6, y), (x + 9, y + 5), (x + 7, y + 7)])
        elif obj.kind == "boat":
            pygame.draw.rect(surface, COLORS.danger, (x + 2, y, 5, 8))
            pygame.draw.polygon(surface, (173, 53, 53), [(x, y + 7), (x + 9, y + 7), (x + 7, y + 11), (x + 2, y + 11)])
            pygame.draw.rect(surface, COLORS.text, (x + 3, y + 2, 3, 2))
        else:
            pygame.draw.rect(surface, COLORS.accent, (x, y, 7, 9))
            pygame.draw.rect(surface, COLORS.background, (x + 2, y + 2, 3, 5))
            pygame.draw.rect(surface, COLORS.accent, (x + 3, y + 3, 1, 3))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 49, 106, 36)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 54, color=COLORS.text, size=12, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 71, color=COLORS.food, size=7, center=True)
