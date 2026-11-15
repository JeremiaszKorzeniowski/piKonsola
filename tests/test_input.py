import pygame
from types import SimpleNamespace

from pikonsola.input import KeyboardInput, Key


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
