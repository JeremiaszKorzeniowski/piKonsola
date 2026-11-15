import pygame

from pikonsola.app import ConsoleApp, Screen
from pikonsola.input import InputFrame, Key


class Controls:
    def __init__(self) -> None:
        self.frame = InputFrame()

    def poll(self) -> InputFrame:
        frame = self.frame
        self.frame = InputFrame()
        return frame

    def press(self, key: Key) -> None:
        self.frame = InputFrame(pressed={key}, held={key})

    def close(self) -> None:
        pass


class FinishedProcess:
    returncode = 0

    def poll(self):
        return self.returncode

    def communicate(self):
        return ("Already up to date.\n", None)


def test_update_option_in_key3_menu_opens_update_question() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.POWER
    app.power_selected = 2
    controls.press(Key.A)
    app.update(0.01)
    assert app.screen is Screen.UPDATE_CONFIRM


def test_key2_cancels_update() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.UPDATE_CONFIRM
    controls.press(Key.B)
    app.update(0.01)
    assert app.screen is Screen.LAUNCHER


def test_successful_update_requests_restart(monkeypatch) -> None:
    pygame.display.init()
    controls = Controls()
    app = ConsoleApp(controls)
    captured = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        return FinishedProcess()

    monkeypatch.setattr("pikonsola.app.subprocess.Popen", fake_popen)
    app.screen = Screen.UPDATE_CONFIRM
    controls.press(Key.A)
    app.update(0.01)
    assert app.screen is Screen.UPDATING
    assert captured["command"] == ["git", "pull", "--ff-only", "origin", "main"]

    app.update(0.01)
    assert app.screen is Screen.UPDATE_RESULT
    assert app.update_ok

    app.update(1.6)
    assert app.restart_requested
    assert not app.running
