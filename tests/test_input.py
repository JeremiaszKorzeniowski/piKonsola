import pygame
from types import SimpleNamespace

from pikonsola.input import KeyboardInput, Key


class FakeGamepad:
    def __init__(self, *, axes=(0.0, 0.0), buttons=(), hat=(0, 0)) -> None:
        self.axes = axes
        self.buttons = set(buttons)
        self.hat = hat

    def get_numaxes(self):
        return len(self.axes)

    def get_axis(self, index):
        return self.axes[index]

    def get_numbuttons(self):
        return 15

    def get_button(self, index):
        return index in self.buttons

    def get_numhats(self):
        return 1

    def get_hat(self, index):
        return self.hat


def test_xbox_a_button_maps_to_a(monkeypatch) -> None:
    controls = KeyboardInput()
    events = [[SimpleNamespace(type=pygame.JOYBUTTONDOWN, button=0)], [SimpleNamespace(type=pygame.JOYBUTTONUP, button=0)]]
    monkeypatch.setattr(pygame.event, "get", lambda: events.pop(0))
    frame = controls.poll()
    assert frame.just_pressed(Key.A)
    assert frame.is_held(Key.A)
    assert not controls.poll().is_held(Key.A)


def test_xbox_stick_maps_to_direction_with_dead_zone(monkeypatch) -> None:
    controls = KeyboardInput()
    events = [
        [SimpleNamespace(type=pygame.JOYAXISMOTION, axis=0, value=-0.8)],
        [SimpleNamespace(type=pygame.JOYAXISMOTION, axis=0, value=0.0)],
    ]
    monkeypatch.setattr(pygame.event, "get", lambda: events.pop(0))
    first_frame = controls.poll()
    assert first_frame.just_pressed(Key.LEFT)
    assert first_frame.is_held(Key.LEFT)
    assert not controls.poll().is_held(Key.LEFT)


def test_xbox_dpad_maps_to_direction(monkeypatch) -> None:
    controls = KeyboardInput()
    events = [
        [SimpleNamespace(type=pygame.JOYHATMOTION, value=(0, 1))],
        [SimpleNamespace(type=pygame.JOYHATMOTION, value=(0, 0))],
    ]
    monkeypatch.setattr(pygame.event, "get", lambda: events.pop(0))
    first_frame = controls.poll()
    assert first_frame.just_pressed(Key.UP)
    assert first_frame.is_held(Key.UP)
    assert not controls.poll().is_held(Key.UP)


def test_gamepad_state_is_polled_without_sdl_events(monkeypatch) -> None:
    controls = KeyboardInput()
    controls._gamepads = {1: FakeGamepad(axes=(-0.8, 0.0), buttons={0}, hat=(0, 1))}
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    frame = controls.poll()
    assert frame.just_pressed(Key.A)
    assert frame.is_held(Key.A)
    assert frame.just_pressed(Key.LEFT)
    assert frame.is_held(Key.UP)
