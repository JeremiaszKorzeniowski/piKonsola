import pygame

from pikonsola.games.knight_tour import KnightTour, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_starts_on_a1_with_two_legal_destinations() -> None:
    game = KnightTour()

    assert game.position == (0, 0)
    assert game.square_name == "A1"
    assert game.visited == {(0, 0)}
    assert game.destinations == [(2, 1), (1, 2)]


def test_pad_changes_selection_and_a_confirms_jump() -> None:
    game = KnightTour()
    first = game.selected_destination

    game.update(0, press(Key.RIGHT))
    assert game.selected_destination != first
    chosen = game.selected_destination

    game.update(0, press(Key.A))
    assert game.position == chosen
    assert chosen in game.visited
    assert len(game.visited) == 2


def test_landing_on_visited_square_ends_game() -> None:
    game = KnightTour()
    game._land((2, 1))
    assert (0, 0) in game.destinations

    game.selection = game.destinations.index((0, 0))
    game.update(0, press(Key.A))

    assert game.position == (0, 0)
    assert game.status is Status.LOST
    assert len(game.visited) == 2


def test_visiting_last_new_square_wins() -> None:
    game = KnightTour()
    last = (2, 1)
    game.visited = {
        (x, y)
        for y in range(8)
        for x in range(8)
        if (x, y) != last
    }

    game._land(last)

    assert game.status is Status.WON
    assert len(game.visited) == 64


def test_a_restarts_after_game_over_and_b_resets_during_play() -> None:
    game = KnightTour()
    game._land((2, 1))
    game.update(0, press(Key.B))
    assert game.position == (0, 0)
    assert game.visited == {(0, 0)}

    game.status = Status.LOST
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING
    assert game.position == (0, 0)


def test_draws_every_state() -> None:
    pygame.font.init()
    surface = pygame.Surface((128, 128))
    game = KnightTour()

    for status in Status:
        game.status = status
        game.draw(surface)
