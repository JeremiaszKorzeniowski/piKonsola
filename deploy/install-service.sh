#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ "$(id -un)" != "pi" ]; then
    echo "Instalator zakłada użytkownika pi. Aktualny użytkownik: $(id -un)" >&2
    exit 1
fi

sudo visudo -cf "$PROJECT_DIR/deploy/pikonsola-sudoers"
sudo install -m 0440 "$PROJECT_DIR/deploy/pikonsola-sudoers" /etc/sudoers.d/pikonsola
sudo install -m 0644 "$PROJECT_DIR/deploy/pikonsola.service" /etc/systemd/system/pikonsola.service
sudo systemctl daemon-reload

# Usuń poprzedni link z multi-user.target i włącz wcześniejszy basic.target.
sudo systemctl disable pikonsola.service >/dev/null 2>&1 || true
sudo systemctl enable pikonsola.service
sudo systemctl restart pikonsola.service

echo "piKonsola działa. Stan:"
systemctl --no-pager --full status pikonsola.service || true
