import pygame

from pikonsola.app import LAUNCHER_VISIBLE_GAMES, ConsoleApp
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


def test_key2_toggles_day_and_night_modes() -> None:
    controls = Controls()
    app = ConsoleApp(controls)

    controls.press(Key.B)
    app.update(0.01)
    assert app.color_mode == "day"
    assert COLORS.background == DAY_PALETTE.background

    controls.press(Key.B)
    app.update(0.01)
    assert app.color_mode == "night"
    assert COLORS.background == NIGHT_PALETTE.background
