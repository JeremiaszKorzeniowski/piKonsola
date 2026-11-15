# piKonsola

Minimalna konsola retro dla Raspberry Pi Zero W i ekranu Waveshare 1.44" LCD HAT
(ST7735S, 128x128). Pierwsza wersja zawiera launcher oraz grę **Nibbles**.
Na Raspberry Pi obraz jest wysyłany bezpośrednio do LCD przez SPI — projekt nie
wymaga starego sterownika `fbcp` ani środowiska graficznego.

## Sterowanie

| HAT | Klawiatura testowa | Funkcja |
|---|---|---|
| joystick | strzałki | ruch / wybór |
| wciśnięcie joysticka | Enter | start / zatwierdź |
| KEY1 | Z | A |
| KEY2 | X | B / powrót |
| KEY3 | Escape | menu konsoli |

Przytrzymanie `KEY3` przez 1,5 sekundy wraca z gry do launchera. W launcherze
`KEY3` otwiera ekran wyłączenia, a `KEY2` ekran aktualizacji.

## Aktualizacja z menu

W launcherze naciśnij `KEY2`, a następnie potwierdź przez `KEY1` lub klik
joysticka. Konsola wykonuje bezpieczne `git pull --ff-only origin main`, więc nie
nadpisze lokalnych zmian. Po udanym pobraniu aplikacja sama uruchamia się ponownie.
Przy błędzie szczegóły trafiają do dziennika usługi:

```bash
journalctl -u pikonsola.service -n 50 --no-pager
```

## Uruchomienie na komputerze

Wymagany jest Python 3.9+.

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pikonsola
```

Program wyświetla powiększone okno, ale zawsze rysuje w rozdzielczości 128x128.

## Instalacja na Raspberry Pi

Zalecany jest aktualny Raspberry Pi OS Lite 32-bit. Włącz SPI i zainstaluj pakiety:

```bash
sudo raspi-config nonint do_spi 0
sudo apt update
sudo apt install -y git python3-pygame python3-gpiozero python3-rpi-lgpio \
  python3-pil python3-luma.lcd python3-spidev
git clone https://github.com/JeremiaszKorzeniowski/piKonsola.git /home/pi/piKonsola
cd /home/pi/piKonsola
PIKONSOLA_DISPLAY=spi PYTHONPATH=src python3 -m pikonsola
```

Po ostatnim poleceniu na LCD powinien pojawić się launcher. Zatrzymaj test przez
`Ctrl+C`. Jeśli obraz jest obrócony, uruchom test ponownie z wartością
`PIKONSOLA_ROTATE=1`, `2` albo `3`.

Program sam rozpoznaje Raspberry Pi i używa wejść GPIO. Mapowanie pinów BCM:

- joystick: góra 6, dół 19, lewo 5, prawo 26, klik 13,
- KEY1 21, KEY2 20, KEY3 16.

Można wymusić tryb klawiatury poleceniem:

```bash
PIKONSOLA_INPUT=keyboard python3 -m pikonsola
```

Na komputerze można jawnie wymusić zwykłe okno:

```bash
PIKONSOLA_DISPLAY=window python3 -m pikonsola
```

## Autostart

Po skopiowaniu projektu do `/home/pi/piKonsola`:

```bash
bash deploy/install-service.sh
```

Instalator włącza autostart na wcześniejszym etapie `basic.target`, instaluje
ograniczoną regułę bezpiecznego wyłączania i uruchamia usługę ponownie. Zakłada
użytkownika `pi`. Jeżeli system ma inną nazwę użytkownika, trzeba zmienić pola
`User`, `WorkingDirectory` i `ExecStart` w usłudze oraz użytkownika w pliku
`deploy/pikonsola-sudoers`.

## Bezpieczne wyłączanie

Instalator usługi pozwala launcherowi uruchamiać wyłącznie jedno polecenie
administracyjne — `/usr/sbin/poweroff`. Aby wyłączyć konsolę, naciśnij `KEY3`
w launcherze, a następnie potwierdź przez `KEY1` albo klik joysticka.

Zainstalowana reguła sudoers ma postać:

```text
pi ALL=(root) NOPASSWD: /usr/sbin/poweroff
```

Nie odłączaj zasilania, dopóki zielona dioda aktywności karty microSD nie przestanie
migać.

