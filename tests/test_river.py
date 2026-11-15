from pikonsola.games.river import Bridge, Bullet, River, RiverObject, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_player_moves_but_stays_on_screen() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    start = game.player_x
    game.update(0.1, InputFrame(held={Key.RIGHT}))
    assert game.player_x > start
    game.update(10, InputFrame(held={Key.RIGHT, Key.DOWN}))
    assert game.player_x <= 116
    assert game.player_y <= 115


def test_water_stripes_move_down_the_screen() -> None:
    game = River(seed=1)
    first_rows = list(game._stripe_rows())
    game.distance = 3
    moved_rows = list(game._stripe_rows())
    assert moved_rows[1] == first_rows[1] + 3


def test_generated_river_never_gets_narrower_than_half_screen() -> None:
    game = River(seed=1)
    for _ in range(200):
        game._move_river(0.1)
        assert all(section.right - section.left >= 64 for section in game.sections)


def test_hitting_bank_costs_life_and_returns_player_to_water() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.player_x = 0
    game._resolve_collisions()
    assert game.lives == 2
    left, right = game._river_bounds(game.player_y)
    assert left + 2 <= game.player_x
    assert game.player_x + 11 <= right - 2


def test_player_can_shoot() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.update(0, press(Key.A))
    assert len(game.bullets) == 1


def test_bullet_destroys_boat_and_scores() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    target = RiverObject(50, 50, "boat")
    game.objects = [target]
    game.bullets = [Bullet(53, 53)]
    game._resolve_collisions()
    assert target not in game.objects
    assert game.score == 20


def test_fuel_is_collected_without_losing_life() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.fuel = 70
    game.objects = [RiverObject(game.player_x + 2, game.player_y, "fuel")]
    game._resolve_collisions()
    assert game.objects == []
    assert game.score == 25
    assert game.lives == 3
    assert game.fuel == 100


def test_fuel_falls_during_flight() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.update(1, InputFrame())
    assert game.fuel < 100


def test_empty_fuel_ends_game() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.fuel = 1
    game.update(1, InputFrame())
    assert game.status is Status.GAME_OVER
    assert game.game_over_reason == "BRAK PALIWA"


def test_bridge_can_be_destroyed_and_increases_object_density() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    bridge = Bridge(50)
    game.bridges = [bridge]
    bridge_rect = game._bridge_rect(bridge)
    game.bullets = [Bullet(bridge_rect.centerx, bridge_rect.y)]
    old_interval = game._spawn_interval()
    game._resolve_collisions()
    assert game.bridges == []
    assert game.score == 50
    assert game.stage == 1
    assert game._spawn_interval() < old_interval


def test_bridge_appears_after_enough_distance() -> None:
    game = River(seed=1)
    game.distance = game.next_bridge_distance
    game._spawn_bridge()
    assert len(game.bridges) == 1


def test_three_crashes_end_game() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    for expected_lives in (2, 1, 0):
        game.invulnerable = 0
        game.objects = [RiverObject(game.player_x, game.player_y, "rock")]
        game._resolve_collisions()
        assert game.lives == expected_lives
    assert game.status is Status.GAME_OVER
