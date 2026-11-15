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

    # Standardowy układ przycisków pada Xbox widziany przez SDL/pygame.
    BUTTON_MAP = {
        0: Key.A,
        1: Key.B,
        6: Key.MENU,  # Back / View
        7: Key.START,
        11: Key.UP,
        12: Key.DOWN,
        13: Key.LEFT,
        14: Key.RIGHT,
    }
    DEAD_ZONE = 0.45

    def __init__(self) -> None:
        pygame.joystick.init()
        self._gamepads: dict[int, pygame.joystick.JoystickType] = {}
        for index in range(pygame.joystick.get_count()):
            self._add_gamepad(index)
        self._keyboard_held: set[Key] = set()
        self._controller_buttons: set[Key] = set()
        self._controller_directions: set[Key] = set()
        self._axes = {0: 0.0, 1: 0.0}
        self._menu_since: Optional[float] = None

    def poll(self) -> InputFrame:
        pressed: set[Key] = set()
        previous_controller = self._controller_buttons | self._controller_directions
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pressed.add(Key.MENU)
                self._keyboard_held.add(Key.MENU)
            elif event.type == pygame.KEYDOWN and event.key in self.KEYMAP:
                key = self.KEYMAP[event.key]
                if key not in self._keyboard_held:
                    pressed.add(key)
                self._keyboard_held.add(key)
            elif event.type == pygame.KEYUP and event.key in self.KEYMAP:
                self._keyboard_held.discard(self.KEYMAP[event.key])
            elif event.type == pygame.JOYDEVICEADDED:
                self._add_gamepad(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                joystick = self._gamepads.pop(event.instance_id, None)
                if joystick is not None:
                    print(f"Odłączono pad USB: {joystick.get_name()}", flush=True)
            elif event.type == pygame.JOYBUTTONDOWN and event.button in self.BUTTON_MAP:
                key = self.BUTTON_MAP[event.button]
                if key not in self._controller_buttons:
                    pressed.add(key)
                self._controller_buttons.add(key)
            elif event.type == pygame.JOYBUTTONUP and event.button in self.BUTTON_MAP:
                self._controller_buttons.discard(self.BUTTON_MAP[event.button])
            elif event.type == pygame.JOYHATMOTION:
                previous = set(self._controller_directions)
                self._set_hat(event.value)
                pressed.update(self._controller_directions - previous)
            elif event.type == pygame.JOYAXISMOTION and event.axis in self._axes:
                previous = set(self._controller_directions)
                self._axes[event.axis] = event.value
                self._set_axis_directions()
                pressed.update(self._controller_directions - previous)

        # Bezpośredni odczyt działa także wtedy, gdy sterownik SDL nie wysyła
        # zdarzeń osi/przycisków przy ukrytym ekranie na Raspberry Pi OS Lite.
        if self._gamepads:
            self._poll_gamepads()
            current_controller = self._controller_buttons | self._controller_directions
            pressed.update(current_controller - previous_controller)

        held = self._keyboard_held | self._controller_buttons | self._controller_directions
        now = time.monotonic()
        if Key.MENU in held:
            if self._menu_since is None:
                self._menu_since = now
            menu_seconds = now - self._menu_since
        else:
            self._menu_since = None
            menu_seconds = 0.0
        return InputFrame(pressed, held, menu_seconds)

    def _add_gamepad(self, index: int) -> None:
        joystick = pygame.joystick.Joystick(index)
        joystick.init()
        instance_id = joystick.get_instance_id()
        if instance_id in self._gamepads:
            self._gamepads[instance_id] = joystick
            return
        self._gamepads[instance_id] = joystick
        print(f"Wykryto pad USB: {joystick.get_name()}", flush=True)

    def _poll_gamepads(self) -> None:
        buttons: set[Key] = set()
        directions: set[Key] = set()
        for joystick in self._gamepads.values():
            for button, key in self.BUTTON_MAP.items():
                if button < joystick.get_numbuttons() and joystick.get_button(button):
                    buttons.add(key)

            if joystick.get_numaxes() >= 2:
                x, y = joystick.get_axis(0), joystick.get_axis(1)
                if x <= -self.DEAD_ZONE:
                    directions.add(Key.LEFT)
                elif x >= self.DEAD_ZONE:
                    directions.add(Key.RIGHT)
                if y <= -self.DEAD_ZONE:
                    directions.add(Key.UP)
                elif y >= self.DEAD_ZONE:
                    directions.add(Key.DOWN)

            for hat_index in range(joystick.get_numhats()):
                x, y = joystick.get_hat(hat_index)
                if x < 0:
                    directions.add(Key.LEFT)
                elif x > 0:
                    directions.add(Key.RIGHT)
                if y < 0:
                    directions.add(Key.DOWN)
                elif y > 0:
                    directions.add(Key.UP)

        self._controller_buttons = buttons
        self._controller_directions = directions

    def _set_hat(self, value: tuple[int, int]) -> None:
        x, y = value
        self._controller_directions -= {Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT}
        if x < 0:
            self._controller_directions.add(Key.LEFT)
        elif x > 0:
            self._controller_directions.add(Key.RIGHT)
        if y < 0:
            self._controller_directions.add(Key.DOWN)
        elif y > 0:
            self._controller_directions.add(Key.UP)

    def _set_axis_directions(self) -> None:
        self._controller_directions -= {Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT}
        x, y = self._axes[0], self._axes[1]
        if x <= -self.DEAD_ZONE:
            self._controller_directions.add(Key.LEFT)
        elif x >= self.DEAD_ZONE:
            self._controller_directions.add(Key.RIGHT)
        if y <= -self.DEAD_ZONE:
            self._controller_directions.add(Key.UP)
        elif y >= self.DEAD_ZONE:
            self._controller_directions.add(Key.DOWN)

    def close(self) -> None:
        for joystick in self._gamepads.values():
            joystick.quit()
        self._gamepads.clear()


class CompositeInput(InputBackend):
    def __init__(self, *backends: InputBackend) -> None:
        self.backends = backends

    def poll(self) -> InputFrame:
        frames = [backend.poll() for backend in self.backends]
        return InputFrame(
            pressed=set().union(*(frame.pressed for frame in frames)),
            held=set().union(*(frame.held for frame in frames)),
            menu_held_seconds=max(frame.menu_held_seconds for frame in frames),
        )

    def close(self) -> None:
        for backend in self.backends:
            backend.close()


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
            return CompositeInput(GPIOInput(), KeyboardInput())
        except (ImportError, OSError) as exc:
            if requested == "gpio":
                raise RuntimeError("Nie udało się uruchomić wejścia GPIO") from exc
    return KeyboardInput()

