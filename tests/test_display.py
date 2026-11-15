from pikonsola import display


def test_explicit_window_display(monkeypatch) -> None:
    monkeypatch.setenv("PIKONSOLA_DISPLAY", "window")
    assert display.selected_display() == "window"


def test_explicit_spi_display(monkeypatch) -> None:
    monkeypatch.setenv("PIKONSOLA_DISPLAY", "spi")
    assert display.selected_display() == "spi"


def test_invalid_display_value(monkeypatch) -> None:
    monkeypatch.setenv("PIKONSOLA_DISPLAY", "telewizor")
    try:
        display.selected_display()
    except ValueError as exc:
        assert "PIKONSOLA_DISPLAY" in str(exc)
    else:
        raise AssertionError("Nieprawidłowa wartość powinna zgłosić ValueError")
