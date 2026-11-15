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
