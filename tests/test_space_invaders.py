from pikonsola.games.space_invaders import Bullet, SpaceInvaders, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = SpaceInvaders(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_player_moves_and_stays_on_screen() -> None:
    game = SpaceInvaders(seed=1)
    game.update(0, press(Key.A))
    start = game.player_x
    game.update(0.1, InputFrame(held={Key.RIGHT}))
    assert game.player_x > start
    game.update(10, InputFrame(held={Key.RIGHT}))
    assert game.player_x <= 115


def test_player_can_shoot() -> None:
    game = SpaceInvaders(seed=1)
    game.update(0, press(Key.A))
    game.update(0, press(Key.A))
    assert len(game.player_bullets) == 1


def test_invaders_start_as_three_rows_of_four_and_move_sideways() -> None:
    game = SpaceInvaders(seed=1)
    assert len(game.invaders) == 12
    assert [sum(invader.row == row for invader in game.invaders) for row in range(3)] == [4, 4, 4]
    game.update(0, press(Key.A))
    initial_positions = [(invader.x, invader.y) for invader in game.invaders]
    game.update(1.0, InputFrame())
    assert all(invader.x > x for invader, (x, _) in zip(game.invaders, initial_positions))
    assert all(invader.y == y for invader, (_, y) in zip(game.invaders, initial_positions))


def test_bullet_destroys_invader_and_scores() -> None:
    game = SpaceInvaders(seed=1)
    game.update(0, press(Key.A))
    target = game.invaders[0]
    game.player_bullets = [Bullet(target.x + 4, target.y + 2)]
    game._resolve_collisions()
    assert not target.alive
    assert game.score == 30


def test_destroying_last_invader_wins() -> None:
    game = SpaceInvaders(seed=1)
    game.update(0, press(Key.A))
    for invader in game.invaders:
        invader.alive = False
    game.update(0, InputFrame())
    assert game.status is Status.WON
