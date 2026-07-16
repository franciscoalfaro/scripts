# PRTG Capture → Telegram

Sistema que captura periódicamente la página de sensores de PRTG
usando Chromium headless (Playwright) y la envía por Telegram.

## Arquitectura

```
┌──────────────────────────────────────────────────┐
│  VM (Docker Linux)                               │
│                                                  │
│  prtg-capture (:8080)   ← Chromium headless      │
│    GET /capture → screenshot PRTG → PNG          │
│                                                  │
│  n8n (:5678)            ← Docker (separado)      │
│    Cron → HTTP Request → Telegram Bot            │
└──────────────────────────────────────────────────┘
         │
         ▼ Telegram
    Screenshot cada 30 min
```

## Requisitos

- Docker Desktop o Docker Engine en Linux
- Acceso a la URL de PRTG desde la VM
- Bot de Telegram (ver `SETUP-TELEGRAM.md`)

## Archivos

| Archivo | Descripcion |
|---------|-------------|
| `capture-server.py` | Servidor HTTP con Playwright (Chromium headless) |
| `Dockerfile` | Imagen Linux + Python + Chromium |
| `docker-compose.yml` | Orquestacion del servicio |
| `.env` / `.env.example` | Configuracion y credenciales de PRTG |
| `requirements.txt` | Dependencias Python |
| `prtg-capture-workflow.json` | Workflow para importar en n8n |
| `SETUP-TELEGRAM.md` | Guia para crear el Bot de Telegram |

---

## Paso 1: Configurar credenciales

Copiar el archivo de ejemplo y llenar con las credenciales de PRTG:

```bash
cp .env.example .env
```

Editar `.env`:

```env
PRTG_URL=https://186.10.70.44/sensors.htm?id=0&filter_status=5
PRTG_LOGIN_URL=https://186.10.70.44/index.htm
PRTG_USER=tu_usuario
PRTG_PASS=tu_password
SERVER_PORT=8080
SCREENSHOT_WIDTH=1920
SCREENSHOT_HEIGHT=1080
```

Si PRTG no requiere login, dejar `PRTG_USER` y `PRTG_PASS` vacios.

## Paso 2: Levantar contenedor

```bash
docker compose up -d --build
```

Verificar que este corriendo:

```bash
docker ps --filter name=prtg-capture
```

## Paso 3: Verificar que funciona

```bash
# Health check
curl http://localhost:8080/health

# Captura de prueba
curl -o test.png http://localhost:8080/capture

# Abrir test.png para verificar la imagen
```

Endpoints disponibles:

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/capture` | GET | Captura full page de PRTG, devuelve PNG |
| `/capture?url=<otra_url>` | GET | Captura una URL especifica |
| `/health` | GET | Health check, retorna `OK` |

## Paso 4: Importar workflow en n8n

1. Abrir `http://localhost:5678`
2. **New Workflow** > **Import from File** > `prtg-capture-workflow.json`
3. **Settings > Credentials > New** > **Telegram API** > pegar Bot Token
4. Abrir nodo **"Enviar a Telegram"** > seleccionar la credencial creada
5. Hacer clic en **"Execute Workflow"** para probar manualmente
6. **Activar** el workflow para que corra automaticamente cada 30 minutos

## Comandos utiles

```bash
# Ver logs en tiempo real
docker logs -f prtg-capture

# Reiniciar contenedor
docker compose restart

# Detener
docker compose down

# Reconstruir (tras cambios en capture-server.py)
docker compose up -d --build
```

---

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| `ERR_CONNECTION_REFUSED` | PRTG no accesible desde el contenedor, verificar red |
| `net::ERR_CERT` | SSL self-signed, ya se ignora automaticamente |
| Login falla | Verificar selectores del form de login en `do_login()` en `capture-server.py` |
| Captura vacia o negra | PRTG puede requerir mas tiempo, ajustar `page.wait_for_timeout()` |
| Telegram no llega | Verificar Bot Token y Chat ID en la credencial de n8n |
| Puerto 8080 ocupado | Cambiar `SERVER_PORT` en `.env` y el puerto en `docker-compose.yml` |
| `pip: not found` en build | Verificar que el Dockerfile use `python:3.12-slim` como base |
| Contenedor se reinicia | Revisar logs con `docker logs prtg-capture` |
