# Guia: Configurar Bot de Telegram para captura PRTG

## Paso 1: Crear el Bot

1. Abrir **Telegram** y buscar **@BotFather**
2. Enviar comando: `/newbot`
3. Elegir un nombre para el bot (ej: `PRTG Capture Bot`)
4. Elegir un username (debe terminar en `bot`, ej: `prtg_capture_bot`)
5. BotFather te da el **Bot Token** (formato: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)
6. **Copiar y guardar ese token**

## Paso 2: Obtener el Chat ID

1. Abrir Telegram y buscar el bot que creaste
2. Enviarle un mensaje (cualquier cosa, ej: `hola`)
3. Abrir el navegador y ir a:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
   Reemplazar `<TU_TOKEN>` con el token del paso anterior
4. Buscar en la respuesta:
   ```json
   "chat": {
     "id": 123456789
   }
   ```
5. **Copiar ese número** (es tu Chat ID)

## Paso 3: Configurar credenciales en n8n

1. Abrir n8n (`http://localhost:5678`)
2. Ir a **Settings** → **Credentials** → **New**
3. Buscar **Telegram API**
4. Pegar el **Bot Token** en el campo correspondiente
5. Guardar

## Paso 4: Importar y configurar el workflow

1. **New Workflow** → **Import from File**
2. Seleccionar: `C:\scripts\prtg-capture-workflow.json`
3. Abrir el nodo **"Enviar a Telegram"**
4. En **Credentials** → seleccionar el bot que creaste en el Paso 3
5. En **Chat ID** → pegar el Chat ID del Paso 2
6. Guardar

## Paso 5: Activar

1. Hacer clic en **Active** (arriba a la derecha)
2. La primera ejecucion se puede probar con **Execute Workflow** (boton manual)

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| "Unauthorized" en Telegram | Verificar que el Bot Token sea correcto |
| No llega el mensaje | Verificar que el Chat ID sea correcto y que hayas enviado un mensaje al bot primero |
| "Ventana no encontrada" | Verificar que Remote Desktop Manager este abierto con la sesion VM |
| Captura negra o vacia | La ventana RDP puede estar minimizada, verificar que este visible en pantalla |
