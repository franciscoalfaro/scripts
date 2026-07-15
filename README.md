# PRTG Capture → Telegram

Sistema que captura periódicamente la ventana de PRTG (visible a través de
Remote Desktop Manager en un segundo monitor) y la envía por Telegram.

## Arquitectura

```
┌─────────────────────────────────────────────┐
│  Windows (equipo local)                     │
│                                             │
│  capture-server.py (:8080)                  │
│    GET /capture → screenshot → PNG          │
│                                             │
│  n8n (Docker)                               │
│    Cron → HTTP Request → Telegram Bot       │
└─────────────────────────────────────────────┘
         │
         ▼ Telegram
    📱 Screenshot cada 30 min
```

## Requisitos

- Windows 10/11
- Python 3.10+ con pip
- Docker Desktop con n8n
- Bot de Telegram

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `capture-server.py` | Servidor HTTP que toma screenshots |
| `capture-window.ps1` | Script PowerShell alternativo (opcional) |
| `prtg-capture-workflow.json` | Workflow para importar en n8n |
| `SETUP-TELEGRAM.md` | Guía para crear el Bot de Telegram |

---

## Paso 1: Instalar dependencias de Python

```powershell
pip install Pillow pywin32 mss
```

## Paso 2: Crear Bot de Telegram

Ver `SETUP-TELEGRAM.md` para instrucciones detalladas.

Resumen:
1. Buscar **@BotFather** en Telegram
2. Enviar `/newbot` → elegir nombre y username
3. Copiar **Bot Token**
4. Enviar un mensaje al bot
5. Abrir `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Copiar el `chat.id`

## Paso 3: Iniciar servidor de captura

```powershell
python C:\scripts\capture-server.py
```

Verificar que funcione:
```
http://localhost:8080/health
http://localhost:8080/capture?window=Remote%20Desktop%20Manager
```

El servidor debe estar corriendo siempre que se quieran enviar capturas.

## Paso 4: Importar workflow en n8n

1. Abrir `http://localhost:5678`
2. **New Workflow** → **Import from File** → `prtg-capture-workflow.json`
3. **Settings → Credentials → New** → **Telegram API** → pegar Bot Token
4. Abrir nodo **"Enviar a Telegram"** → seleccionar la credencial creada
5. Hacer clic en **"Execute Workflow"** para probar manualmente
6. **Activar** el workflow para que corra automáticamente cada 30 minutos

## Paso 5: Ejecutar servidor automáticamente (opcional)

Para que el servidor de captura arranque solo al iniciar Windows:

1. Abrir **Task Scheduler** (`taskschd.msc`)
2. **Create Basic Task** → nombre: `PRTG Capture Server`
3. **Trigger**: When I log on
4. **Action**: Start a program
   - Program: `python`
   - Arguments: `C:\scripts\capture-server.py`
5. Finalizar y guardar

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `/bin/sh: powershell: not found` | El workflow usa HTTP Request, no Execute Command |
| Ventana no encontrada | Verificar que RDP esté abierto con la VM |
| Captura negra | La ventana RDP no está en pantalla, hacerla visible |
| Telegram no llega | Verificar Bot Token y Chat ID en la credencial de n8n |
| Puerto 8080 ocupado | Cambiar puerto en `capture-server.py` y en el workflow |
| `Access Denied` en HttpListener | Usar Python (no PowerShell) como servidor |
