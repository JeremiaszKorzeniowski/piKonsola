from __future__ import annotations

import os
import platform
from typing import Optional

import pygame

from .config import HEIGHT, WIDTH, window_scale


class DisplayOutput:
    """Destination for the logical 128x128 pygame canvas."""

    def present(self, canvas: pygame.Surface) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class WindowOutput(DisplayOutput):
    def __init__(self) -> None:
        pygame.display.set_caption("piKonsola")
        fullscreen = os.getenv("PIKONSOLA_FULLSCREEN", "0").lower() == "1"
        if fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            scale = window_scale()
            self.window = pygame.display.set_mode((WIDTH * scale, HEIGHT * scale))

    def present(self, canvas: pygame.Surface) -> None:
        if self.window.get_size() == (WIDTH, HEIGHT):
            self.window.blit(canvas, (0, 0))
        else:
            pygame.transform.scale(canvas, self.window.get_size(), self.window)
        pygame.display.flip()


class ST7735Output(DisplayOutput):
    """Direct SPI output for the Waveshare 1.44-inch LCD HAT (SKU 13891)."""

    def __init__(self) -> None:
        try:
            from gpiozero import DigitalOutputDevice
            from luma.core.interface.serial import spi
            from luma.lcd.device import st7735
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Brak bibliotek ekranu. Zainstaluj python3-luma.lcd, "
                "python3-pil i python3-rpi-lgpio."
            ) from exc

        self._image_class = Image
        self._serial = spi(
            port=0,
            device=0,
            gpio_DC=25,
            gpio_RST=27,
            bus_speed_hz=20_000_000,
            transfer_size=4096,
            reset_hold_time=0.1,
            reset_release_time=0.15,
        )
        self._device = st7735(
            serial_interface=self._serial,
            width=WIDTH,
            height=HEIGHT,
            rotate=int(os.getenv("PIKONSOLA_ROTATE", "0")),
            h_offset=int(os.getenv("PIKONSOLA_X_OFFSET", "2")),
            v_offset=int(os.getenv("PIKONSOLA_Y_OFFSET", "3")),
            bgr=True,
            inverse=True,
        )
        self._backlight = DigitalOutputDevice(24, active_high=True, initial_value=True)
        self._last_frame: Optional[bytes] = None

        # Keep pygame's event subsystem initialized on Raspberry Pi OS Lite.
        pygame.display.set_mode((1, 1), pygame.HIDDEN)

    def present(self, canvas: pygame.Surface) -> None:
        frame = pygame.image.tobytes(canvas, "RGB")
        if frame == self._last_frame:
            return
        self._last_frame = frame
        image = self._image_class.frombytes("RGB", (WIDTH, HEIGHT), frame)
        self._device.display(image)

    def close(self) -> None:
        try:
            self._device.clear()
            self._backlight.off()
        finally:
            self._backlight.close()
            self._serial.cleanup()


def selected_display() -> str:
    requested = os.getenv("PIKONSOLA_DISPLAY", "auto").lower()
    if requested not in {"auto", "window", "spi"}:
        raise ValueError("PIKONSOLA_DISPLAY musi mieć wartość auto, window albo spi")
    if requested != "auto":
        return requested

    is_pi = platform.system() == "Linux" and os.path.exists("/proc/device-tree/model")
    return "spi" if is_pi else "window"


def create_display(kind: str) -> DisplayOutput:
    if kind == "spi":
        return ST7735Output()
    return WindowOutput()

