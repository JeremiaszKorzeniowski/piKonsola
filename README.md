# piKonsola

Minimalna konsola retro dla Raspberry Pi Zero W i ekranu Waveshare 1.44" LCD
HAT (ST7735S, 128×128). Obraz jest wysyłany bezpośrednio do LCD przez SPI —
projekt nie wymaga `fbcp` ani środowiska graficznego.

## Gry

Launcher wyświetla gry alfabetycznie. Obecnie dostępne są:

| Gra | Opis |
|---|---|
| Arkanoid | Odbijanie piłki, niszczenie kolorowych klocków i coraz szybsze poziomy. |
| Asteroids | Walka z rozpadającymi się asteroidami, bezwładność i zawijanie ekranu. |
| Czołgi | Obrona bazy w grze inspirowanej Battle City. |
| Defender | Strzelanka z przewijanym światem, radarem i ratowaniem ludzi. |
| Dino | Prosty klon gry z Chrome: bieg, skoki przez kaktusy i coraz szybsze tempo. |
| Invaders | Klon klasycznego Space Invaders. |
| Nibbles | Klasyczny wąż zbierający jedzenie. |
| Pac-Man | Zbieranie punktów w labiryncie i ucieczka przed duchami. |
| Platfus | Platformówka z kluczem, przeszkodami i trzema poziomami. |
| River | Lot nad rzeką, paliwo, przeszkody i mosty do zniszczenia. |
| Skoczek | Wędrówka skoczka po całej szachownicy bez powtarzania pól. |
| Śnieżka 3D | Zimowa strzelanka FPP w stylu Wolfenstein 3D. |
| Sokoban | Logiczne przesuwanie skrzyń na wyznaczone cele. |
| Tetris | Plansza 10×20, siedem rodzajów klocków, poziomy i podgląd kolejnego elementu. |

## Sterowanie

| HAT | Klawiatura testowa | Pad Xbox | Funkcja |
|---|---|---|---|
| joystick | strzałki | lewy drążek / D-pad | ruch lub wybór |
| wciśnięcie joysticka | Enter | Start | start lub zatwierdzenie |
| KEY1 | Z | A | główna akcja |
| KEY2 | X | B | druga akcja lub powrót |
| KEY3 | Escape | Back / View | pauza / menu konsoli |

Pad USB działa równolegle z przyciskami HAT-a. Krótkie naciśnięcie `KEY3`
wstrzymuje lub wznawia dowolną grę, a przytrzymanie go przez 1,5 sekundy wraca
z gry do launchera. Przytrzymanie `KEY2` przez 5 sekund
przełącza tryb dzienny/nocny z dowolnego ekranu, a `KEY3` w launcherze otwiera
menu konsoli. Krótkie naciśnięcie `KEY2` zachowuje swoją funkcję w grach i menu.

### Sterowanie w grach

- **Arkanoid:** lewo/prawo przesuwa paletkę; `KEY1` wypuszcza piłkę.
- **Asteroids:** lewo/prawo obraca statek, góra uruchamia silnik, dół hamuje;
  `KEY1` strzela.
- **Czołgi:** joystick porusza pojazdem, a `KEY1` strzela w kierunku jazdy.
- **Defender:** joystick porusza statkiem, a `KEY1` strzela w kierunku lotu.
- **Dino:** góra, `KEY1` lub kliknięcie joysticka rozpoczyna grę i wykonuje skok.
- **Invaders:** lewo/prawo porusza działkiem; `KEY1` strzela.
- **Platfus:** lewo/prawo porusza bohaterem; góra, `KEY1` lub kliknięcie
  joysticka wykonuje skok.
- **River:** joystick steruje samolotem; `KEY1` strzela.
- **Skoczek:** joystick wybiera legalny cel; `KEY1` zatwierdza skok, a `KEY2`
  resetuje partię.
- **Śnieżka 3D:** góra/dół porusza postacią, lewo/prawo obraca widok;
  `KEY1` rzuca śnieżką.
- **Sokoban:** joystick przesuwa magazyniera; `KEY2` resetuje planszę.
- **Tetris:** lewo/prawo przesuwa klocek, dół przyspiesza opadanie, a góra lub
  `KEY1` obraca; `KEY2` wykonuje twardy zrzut.

## Uruchomienie na komputerze

Wymagany jest Python 3.9+.

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pikonsola
```

Program otwiera powiększone okno, ale zawsze rysuje obraz w rozdzielczości
128×128. Tryb zwykłego okna można wymusić poleceniem:

```bash
PIKONSOLA_DISPLAY=window python3 -m pikonsola
```

## Instalacja na Raspberry Pi

Zalecany jest aktualny Raspberry Pi OS Lite 32-bit.

```bash
sudo raspi-config nonint do_spi 0
sudo apt update
sudo apt install -y git python3-pygame python3-gpiozero python3-rpi-lgpio \
  python3-pil python3-luma.lcd python3-spidev
git clone https://github.com/JeremiaszKorzeniowski/piKonsola.git /home/pi/piKonsola
cd /home/pi/piKonsola
PIKONSOLA_DISPLAY=spi PYTHONPATH=src python3 -m pikonsola
```

Po uruchomieniu launcher powinien pojawić się na LCD. Test można zatrzymać
przez `Ctrl+C`. Jeśli obraz jest obrócony, ustaw `PIKONSOLA_ROTATE` na `1`, `2`
lub `3`.

Program sam rozpoznaje Raspberry Pi i korzysta z wejść GPIO. Mapowanie pinów
BCM:

- joystick: góra 6, dół 19, lewo 5, prawo 26, klik 13;
- KEY1 21, KEY2 20, KEY3 16.

Tryb klawiatury można wymusić poleceniem:

```bash
PIKONSOLA_INPUT=keyboard python3 -m pikonsola
```

## Autostart

Po skopiowaniu projektu do `/home/pi/piKonsola` uruchom:

```bash
bash deploy/install-service.sh
```

Instalator zakłada użytkownika `pi`, włącza usługę na etapie `basic.target`
i instaluje ograniczoną regułę bezpiecznego wyłączania. Przy innej nazwie
użytkownika zmień pola `User`, `WorkingDirectory` i `ExecStart` w
`deploy/pikonsola.service` oraz użytkownika w `deploy/pikonsola-sudoers`.

Po pierwszym dodaniu obsługi pada ponownie uruchom instalator, aby proces dostał
dostęp do grupy urządzeń `input`. Wykrycie pada można sprawdzić poleceniem:

```bash
journalctl -u pikonsola.service -n 30 --no-pager | grep "pad USB"
```

## Aktualizacja z menu

W launcherze naciśnij `KEY3`, wybierz pozycję `AKTUALIZACJA` i potwierdź przez
`KEY1` lub kliknięcie joysticka. Konsola wykona `git pull --ff-only origin
main`, więc nie nadpisze lokalnych zmian. Po udanej aktualizacji aplikacja
uruchomi się ponownie.

W razie błędu sprawdź dziennik usługi:

```bash
journalctl -u pikonsola.service -n 50 --no-pager
```

## Bezpieczne wyłączanie

Menu otwierane przez `KEY3` pozwala wyłączyć, zrestartować lub zaktualizować
urządzenie.
Instalator nadaje aplikacji prawo wyłącznie do tych dwóch poleceń:

```text
pi ALL=(root) NOPASSWD: /usr/sbin/poweroff, /usr/sbin/reboot
```

Nie odłączaj zasilania, dopóki zielona dioda aktywności karty microSD nie
przestanie migać.

## Rozwój i testy

Nową grę dodaje się do listy `self.games` w `src/pikonsola/app.py`. Launcher
sortuje wpisy automatycznie według wyświetlanej nazwy, więc położenia nowego
tytułu nie trzeba ustawiać ręcznie.

Poziomy gier są przechowywane osobno:

- `src/pikonsola/games/platformer_levels/level_*.py` — Platfus;
- `src/pikonsola/games/snow_arena_levels/` — Śnieżka 3D;
- `src/pikonsola/games/sokoban_levels/` — Sokoban.

Uruchomienie testów:

```bash
pytest
```
