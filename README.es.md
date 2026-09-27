<div align="center">

# TURMO Linux

**Sender modular para Linux + GUI en PySide6 para pantallas seriales USB TURMO / UsbMonitor / estilo Turing de 3.5"**

[![CI](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Podman/Docker](https://img.shields.io/badge/Container-GHCR-2496ED?logo=docker&logoColor=white)](https://github.com/ncorrea-13?tab=packages&repo_name=turmo-screen)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](#licencia)

[English](README.md)

</div>

---

Manda un dashboard del sistema, imágenes estáticas, patrones de prueba, o una vista en vivo del resto
de tus máquinas del homelab (vía [Heimdall](https://github.com/kinncj/Heimdall)) a una pantalla serial USB chica por el protocolo
RevA. Proyecto personal, no comercial.

Perfil de pantalla probado:

| Puerto         | Baudrate  | Protocolo | Framebuffer | Formato de píxel |
| -------------- | --------- | --------- | ------------ | ----------------- |
| `/dev/ttyACM0` | `4000000` | `reva`    | `320x480`    | `rgb565le`        |

## Stack

| Capa              | Tecnología                                      |
| ----------------- | ------------------------------------------------ |
| Lenguaje          | Python 3.14                                      |
| GUI               | PySide6 (solo escritorio, no va en la imagen de container) |
| Imagen/píxeles    | Pillow                                           |
| Serial            | pyserial                                         |
| Métricas remotas  | [Heimdall](https://github.com/kinncj/Heimdall) (`heimdall-cli`, binario externo) |
| Container         | Podman/Docker, `python:3.14-alpine`              |

Más: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Inicio rápido

```bash
git clone https://github.com/ncorrea-13/turmo-screen.git
cd turmo-screen
./scripts/install.sh        # crea .venv, instala requirements.txt
./scripts/run_gui.sh
```

Si la pantalla da error de permisos:

```bash
sudo chmod a+rw /dev/ttyACM0
```

Fix permanente:

```bash
sudo usermod -aG dialout "$USER"
sudo usermod -aG uucp "$USER"
reboot
```

`turmo_lite.py`/`turmo_gui.py` son los entry points de CLI/GUI; la implementación real vive en `turmo/`.

## Dashboard del homelab (otras máquinas)

En vez de las métricas de este host, mostrá el estado en vivo de cada máquina de tu homelab:

```bash
python turmo_lite.py --fleet --width 480 --height 320 --orientation landscape
```

Lee `HEIMDALL_HUB` (default `localhost:9090`) y `HEIMDALL_TOKEN` del entorno; necesita
`heimdall-cli` en el `$PATH`. Ver [Desarrollo](#desarrollo-container) /
[Producción](#producción-container) más abajo para el setup en container.

### Setup del daemon en cada máquina

En cada máquina que quieras que turmo muestre, corré `heimdall-daemon` apuntando al hub.
Mantené el token fuera de la línea de comando (mismo motivo que el fix de `fetch_fleet_hosts`)
— usá un archivo de entorno, no `--token`:

```bash
mkdir -p ~/.config/heimdall
printf 'HEIMDALL_TOKEN=<mismo-token-que-el-hub>\n' > ~/.config/heimdall/daemon.env
chmod 600 ~/.config/heimdall/daemon.env

curl -fsSL https://github.com/kinncj/Heimdall/releases/download/v2.7.4/heimdall-daemon_linux_<arch> -o ~/.local/bin/heimdall-daemon
chmod +x ~/.local/bin/heimdall-daemon
```

`~/.config/systemd/user/heimdall-daemon.service`:

```ini
[Unit]
Description=Heimdall daemon

[Service]
EnvironmentFile=%h/.config/heimdall/daemon.env
ExecStart=%h/.local/bin/heimdall-daemon --hub <host-del-hub>:9090 --name %H
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now heimdall-daemon.service
loginctl enable-linger "$USER"   # arranca al boot sin sesión activa
```

TLS (`--tls`/`--tls-ca`) es opcional acá si el hub solo es alcanzable por Tailscale — la mesh
ya encripta el transporte. Agregalo si el hub queda expuesto en una red menos confiable.

## Soporte de GIF

GUI: **Open GIF** → elegí un `.gif` → seteá **GIF FPS** (recomendado `3–8`) → **Play GIF** → **Stop** para cortar el loop.

Los GIF a pantalla completa son lentos: 320×480 RGB565 pesa ~307 KB por frame. GIFs más chicos o con menos FPS andan mejor.

```bash
python turmo_lite.py --gif assets/sample_spinner.gif --gif-loop --gif-fps 8   # loop
python turmo_lite.py --gif assets/sample_spinner.gif --gif-fps 5              # un ciclo
python turmo_lite.py --gif assets/sample_spinner.gif --dry-run gif_first.png  # guarda el primer frame, no envía
```

## Ejemplos de imagen

```bash
python turmo_lite.py --image tu_imagen.png --fit contain --once
```

`--pink-bg`/`--green-to-bg`/`--red-to-blue`/`--force-black` son flags opcionales de limpieza de
color para imágenes con fondo chroma-key; ver `python turmo_lite.py --help`.

## Patrón de prueba

```bash
python turmo_lite.py --test-pattern --once
```

## Desarrollo (container)

`deploy/compose.dev.yaml` buildea `heimdall-hub` + `heimdall-daemon` (auto-monitoreándose el propio
container, solo para tener algo que mostrar) + `turmo` desde el código local — sin necesidad
de registry:

```bash
podman-compose -f deploy/compose.dev.yaml up --build
```

Rebuildear después de cambios de código con `--build` de nuevo. Necesita `/dev/ttyACM0` presente en el host.

## Producción (container)

CI buildea y pushea la imagen `turmo` en cada push a `main` (ver `.github/workflows/ci.yml`),
taggeada `latest`, `<branch>` y `<sha>` en `ghcr.io/<owner>/<repo>`. `heimdall-hub` no lo buildea
CI — asume que ya hay un hub Heimdall real corriendo en la red.

`deploy/compose.prod.yaml`:

```yaml
services:
  turmo:
    image: ghcr.io/ncorrea-13/turmo-screen:latest
    container_name: turmo
    restart: unless-stopped
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
    environment:
      - HEIMDALL_HUB=heimdall-hub:9090
      - HEIMDALL_TOKEN=${HEIMDALL_TOKEN}
    logging:
      driver: journald
```

```bash
podman-compose -f deploy/compose.prod.yaml up -d
```

Notas:

- Cambiá el tag/registry de imagen una vez que el pipeline publique el real.
- `HEIMDALL_HUB`/`HEIMDALL_TOKEN` los lee `turmo/metrics.py:fetch_fleet_hosts`; omití `HEIMDALL_TOKEN` si el hub no tiene token configurado.
- El entrypoint por defecto corre `--fleet --port /dev/ttyACM0 --width 480 --height 320 --orientation landscape` (ver `deploy/Containerfile`); sobreescribí `command:` para otro modo.
- Sin GUI en esta imagen (`PySide6` sacado, ver `requirements-docker.txt`) — solo dashboard headless.

## Testing

```bash
python -m unittest discover tests -v
```

No necesita hardware — el I/O serial está mockeado. Cubre parsing, encoding de píxeles, el
empaquetado de coordenadas RevA, y los casos de error de fetch/render de Heimdall.

## Estructura del proyecto

La implementación real vive en `turmo/`, los entry points (`turmo_lite.py`/`turmo_gui.py`) son
wrappers finos, compatibles hacia atrás. `scripts/` tiene los helpers de instalación/ejecución/
prueba de hardware, `deploy/` tiene los Containerfiles y compose files, `assets/` tiene media de
ejemplo. Layout completo y notas del pipeline de envío: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Sobre el proyecto

Proyecto personal, no comercial. La procedencia de este código en sí (antes de rastrear el
protocolo RevA a su fuente real, y antes del trabajo de Heimdall/containers de este repo) es
turbia — ver [`NOTICE.md`](NOTICE.md) para lo que realmente se sabe.

## Licencia

GPL-3.0-or-later — ver [LICENSE](LICENSE). El protocolo serial RevA en
`turmo/serial_device.py` es una reimplementación de
[turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python)
de Matthieu Houdebine (GPL-3.0-or-later); al ser obra combinada, este repo lleva la misma
licencia. Procedencia completa: [`NOTICE.md`](NOTICE.md).

**Nicolás Correa** — [github.com/ncorrea-13](https://github.com/ncorrea-13)
