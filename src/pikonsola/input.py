from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame


class Key(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    START = "start"
    A = "a"
    B = "b"
    MENU = "menu"


@dataclass
class InputFrame:
    pressed: set[Key] = field(default_factory=set)
    held: set[Key] = field(default_factory=set)
    menu_held_seconds: float = 0.0

    def just_pressed(self, key: Key) -> bool:
        return key in self.pressed

    def is_held(self, key: Key) -> bool:
        return key in self.held


class InputBackend:
    def poll(self) -> InputFrame:
        raise NotImplementedError

    def close(self) -> None:
        pass


class KeyboardInput(InputBackend):
    KEYMAP = {
        pygame.K_UP: Key.UP,
        pygame.K_DOWN: Key.DOWN,
        pygame.K_LEFT: Key.LEFT,
        pygame.K_RIGHT: Key.RIGHT,
        pygame.K_RETURN: Key.START,
        pygame.K_z: Key.A,
        pygame.K_x: Key.B,
        pygame.K_ESCAPE: Key.MENU,
    }

    def __init__(self) -> None:
        self._held: set[Key] = set()
        self._menu_since: Optional[float] = None

    def poll(self) -> InputFrame:
        pressed: set[Key] = set()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pressed.add(Key.MENU)
                self._held.add(Key.MENU)
            elif event.type == pygame.KEYDOWN and event.key in self.KEYMAP:
                key = self.KEYMAP[event.key]
                if key not in self._held:
                    pressed.add(key)
                self._held.add(key)
            elif event.type == pygame.KEYUP and event.key in self.KEYMAP:
                self._held.discard(self.KEYMAP[event.key])

        now = time.monotonic()
        if Key.MENU in self._held:
            if self._menu_since is None:
                self._menu_since = now
            menu_seconds = now - self._menu_since
        else:
            self._menu_since = None
            menu_seconds = 0.0
        return InputFrame(pressed, set(self._held), menu_seconds)


class GPIOInput(InputBackend):
    PINS = {
        Key.UP: 6,
        Key.DOWN: 19,
        Key.LEFT: 5,
        Key.RIGHT: 26,
        Key.START: 13,
        Key.A: 21,
        Key.B: 20,
        Key.MENU: 16,
    }

    def __init__(self) -> None:
        from gpiozero import Button

        self._buttons = {
            key: Button(pin, pull_up=True, bounce_time=0.03)
            for key, pin in self.PINS.items()
        }
        self._previous: set[Key] = set()
        self._menu_since: Optional[float] = None

    def poll(self) -> InputFrame:
        held = {key for key, button in self._buttons.items() if button.is_pressed}
        pressed = held - self._previous
        self._previous = held
        now = time.monotonic()
        if Key.MENU in held:
            if self._menu_since is None:
                self._menu_since = now
            menu_seconds = now - self._menu_since
        else:
            self._menu_since = None
            menu_seconds = 0.0
        return InputFrame(pressed, held, menu_seconds)

    def close(self) -> None:
        for button in self._buttons.values():
            button.close()


def create_input() -> InputBackend:
    requested = os.getenv("PIKONSOLA_INPUT", "auto").lower()
    if requested == "keyboard":
        return KeyboardInput()
    if requested not in {"auto", "gpio"}:
        raise ValueError("PIKONSOLA_INPUT musi mieć wartość auto, keyboard albo gpio")

    is_pi = platform.system() == "Linux" and os.path.exists("/proc/device-tree/model")
    if requested == "gpio" or is_pi:
        try:
            return GPIOInput()
        except (ImportError, OSError) as exc:
            if requested == "gpio":
                raise RuntimeError("Nie udało się uruchomić wejścia GPIO") from exc
    return KeyboardInput()

