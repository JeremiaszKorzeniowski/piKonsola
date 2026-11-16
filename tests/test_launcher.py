import pygame

from pikonsola.app import LAUNCHER_VISIBLE_GAMES, ConsoleApp, Screen
from pikonsola.config import COLORS, DAY_PALETTE, NIGHT_PALETTE
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


def test_launcher_sorts_games_alphabetically() -> None:
    app = ConsoleApp(Controls())

    names = [name for name, _ in app.games]

    assert names == sorted(names, key=str.casefold)


def test_launcher_scrolls_window_to_keep_selection_visible() -> None:
    app = ConsoleApp(Controls())
    app.games.extend((f"GRA {number}", object()) for number in range(4))

    assert app._launcher_window_start() == 0

    app.selected = LAUNCHER_VISIBLE_GAMES
    assert app._launcher_window_start() == 1

    app.selected = len(app.games) - 1
    assert app._launcher_window_start() == len(app.games) - LAUNCHER_VISIBLE_GAMES


def test_launcher_draws_only_visible_games(monkeypatch) -> None:
    pygame.font.init()
    app = ConsoleApp(Controls())
    app.games.extend((f"GRA {number}", object()) for number in range(4))
    app.selected = len(app.games) - 1
    drawn_game_names = []
    game_names = {name for name, _ in app.games}

    def record_text(_surface, value, _x, y, **_kwargs):
        if y in {31, 47, 63, 79} and value in game_names:
            drawn_game_names.append(value)

    monkeypatch.setattr("pikonsola.app.text", record_text)
    app._draw_launcher()

    assert len(drawn_game_names) == LAUNCHER_VISIBLE_GAMES
    assert drawn_game_names[-1] == app.games[-1][0]


def test_holding_key2_toggles_day_and_night_modes_on_any_screen() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.POWER

    for _ in range(49):
        controls.frame = InputFrame(held={Key.B})
        app.update(0.1)
    assert app.color_mode == "night"

    controls.frame = InputFrame(held={Key.B})
    app.update(0.2)
    assert app.color_mode == "day"
    assert COLORS.background == DAY_PALETTE.background

    for _ in range(60):
        controls.frame = InputFrame(held={Key.B})
        app.update(0.1)
    assert app.color_mode == "day"

    app.update(0.1)
    for _ in range(51):
        controls.frame = InputFrame(held={Key.B})
        app.update(0.1)
    assert app.color_mode == "night"
    assert COLORS.background == NIGHT_PALETTE.background


def test_key3_pauses_and_resumes_game() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.GAME
    updates = []
    app.game.update = lambda dt, frame: updates.append((dt, frame))

    controls.press(Key.MENU)
    app.update(0.1)
    assert app.game_paused
    assert updates == []

    app.update(0.1)
    assert updates == []

    controls.press(Key.MENU)
    app.update(0.1)
    assert not app.game_paused
    assert updates == []

    app.update(0.1)
    assert len(updates) == 1


def test_holding_key3_exits_paused_game_to_launcher() -> None:
    controls = Controls()
    app = ConsoleApp(controls)
    app.screen = Screen.GAME
    app.game_paused = True
    controls.frame = InputFrame(held={Key.MENU}, menu_held_seconds=1.5)

    app.update(0.1)

    assert app.screen is Screen.LAUNCHER
    assert not app.game_paused
