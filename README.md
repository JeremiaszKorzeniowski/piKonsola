# piKonsola

Minimalna konsola retro dla Raspberry Pi Zero W i ekranu Waveshare 1.44" LCD HAT
(ST7735S, 128x128). Pierwsza wersja zawiera launcher oraz grę **Nibbles**.

## Sterowanie

| HAT | Klawiatura testowa | Funkcja |
|---|---|---|
| joystick | strzałki | ruch / wybór |
| wciśnięcie joysticka | Enter | start / zatwierdź |
| KEY1 | Z | A |
| KEY2 | X | B / powrót |
| KEY3 | Escape | menu konsoli |

Przytrzymanie `KEY3` przez 1,5 sekundy wraca z gry do launchera. W launcherze
`KEY3` otwiera ekran wyłączenia. Wyłączenie systemu wymaga dodatkowej konfiguracji
opisanej niżej.

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

Zalecany jest Raspberry Pi OS Lite 32-bit. Najpierw włącz SPI przez
`sudo raspi-config` (`Interface Options` -> `SPI`). Sterownik Waveshare/fbcp musi
być skonfigurowany osobno zgodnie z dokumentacją ekranu tak, aby pulpit/framebuffer
był widoczny na LCD.

```bash
sudo apt update
sudo apt install -y python3-pygame python3-gpiozero python3-lgpio git
git clone <adres-repozytorium> /home/pi/piKonsola
cd /home/pi/piKonsola
PYTHONPATH=src python3 -m pikonsola
```

Program sam rozpoznaje Raspberry Pi i używa wejść GPIO. Mapowanie pinów BCM:

- joystick: góra 6, dół 19, lewo 5, prawo 26, klik 13,
- KEY1 21, KEY2 20, KEY3 16.

Można wymusić tryb klawiatury poleceniem:

```bash
PIKONSOLA_INPUT=keyboard python3 -m pikonsola
```

## Autostart

Po skopiowaniu projektu do `/home/pi/piKonsola`:

```bash
sudo cp deploy/pikonsola.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pikonsola.service
```

Usługa zakłada użytkownika `pi`. Jeżeli system ma inną nazwę użytkownika, trzeba
zmienić pola `User`, `WorkingDirectory` i `ExecStart` w pliku usługi.

## Bezpieczne wyłączanie

Domyślnie launcher jedynie zamyka program. Aby przycisk mógł wyłączyć cały system,
ustaw `PIKONSOLA_ALLOW_POWEROFF=1` w usłudze i dodaj precyzyjną regułę sudoers dla
użytkownika konsoli:

```text
pi ALL=(root) NOPASSWD: /usr/sbin/poweroff
```

Nie odłączaj zasilania, dopóki zielona dioda aktywności karty microSD nie przestanie
migać.

