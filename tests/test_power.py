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


def test_power_menu_can_select_restart(monkeypatch) -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.POWER
    commands = []
    monkeypatch.setenv("PIKONSOLA_ALLOW_POWEROFF", "1")
    monkeypatch.setattr("pikonsola.app.subprocess.Popen", lambda command: commands.append(command))

    controls.press(Key.DOWN)
    app.update(0.01)
    assert app.power_selected == 1
    controls.press(Key.A)
    app.update(0.01)

    assert commands == [["sudo", "-n", "/usr/sbin/reboot"]]
    assert not app.running


def test_power_menu_return_option_goes_to_launcher() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.POWER
    app.power_selected = 3
    controls.press(Key.A)
    app.update(0.01)
    assert app.screen is Screen.LAUNCHER
    assert app.running


def test_power_menu_wraps_over_four_options() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.POWER

    controls.press(Key.UP)
    app.update(0.01)

    assert app.power_selected == 3
