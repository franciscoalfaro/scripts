# Servidor HTTP que captura screenshots de PRTG usando Chromium headless (Playwright).
# Recibe peticiones GET, abre la pagina de PRTG en un browser sin ventana,
# toma un screenshot full page y devuelve la imagen como PNG.
# Las credenciales y configuracion se cargan desde un archivo .env.

import os
import io
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuracion desde .env con valores por defecto
PRTG_URL = os.getenv("PRTG_URL", "https://186.10.70.44/sensors.htm?id=0&filter_status=5")
PRTG_LOGIN_URL = os.getenv("PRTG_LOGIN_URL", "https://186.10.70.44/index.htm")
PRTG_USER = os.getenv("PRTG_USER", "")        # Vacio = sin autenticacion
PRTG_PASS = os.getenv("PRTG_PASS", "")        # Vacio = sin autenticacion
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))
SCREENSHOT_WIDTH = int(os.getenv("SCREENSHOT_WIDTH", "1920"))
SCREENSHOT_HEIGHT = int(os.getenv("SCREENSHOT_HEIGHT", "1080"))


def do_login(page):
    """Realiza login en PRTG si se configuraron credenciales en .env.
    Navega a la pagina de login, busca los campos de usuario/password
    usando multiples selectores CSS (por compatibilidad con distintas
    versiones de PRTG), completa el form y hace submit."""
    if not PRTG_USER or not PRTG_PASS:
        return

    print(f"  Login en {PRTG_LOGIN_URL}...")
    page.goto(PRTG_LOGIN_URL, wait_until="networkidle", timeout=30000)

    # PRTG usa diferentes nombres de campos segun la version.
    # Se prueban varios selectores hasta encontrar el correcto.
    user_selectors = [
        'input[name="name"]',       # PRTG clasico
        'input[name="username"]',   # PRTG comun
        'input#name',               # Por ID
        'input[type="text"]',       # Fallback generico
    ]
    pass_selectors = [
        'input[name="password"]',   # PRTG clasico
        'input[name="pass"]',       # Variante corta
        'input#password',           # Por ID
        'input[type="password"]',   # Fallback generico
    ]
    btn_selectors = [
        'input[type="submit"]',     # Boton submit clasico
        'button[type="submit"]',    # Boton HTML5
        'button:has-text("Login")', # Boton con texto "Login"
        'button:has-text("Iniciar")', # Boton en espanol
        'button:has-text("Sign in")', # Boton en ingles
        '#loginbutton',             # PRTG versiones recientes
    ]

    # Buscar campo de usuario (primer selector que matchee)
    user_input = None
    for sel in user_selectors:
        el = page.query_selector(sel)
        if el:
            user_input = el
            break

    # Buscar campo de password
    pass_input = None
    for sel in pass_selectors:
        el = page.query_selector(sel)
        if el:
            pass_input = el
            break

    # Buscar boton de login
    login_btn = None
    for sel in btn_selectors:
        el = page.query_selector(sel)
        if el:
            login_btn = el
            break

    # Si no se encontraron los campos, continuar sin login
    if not user_input or not pass_input:
        print("  WARNING: No se encontraron campos de login, continuando sin auth")
        return

    # Completar credenciales y enviar form
    user_input.fill(PRTG_USER)
    pass_input.fill(PRTG_PASS)

    if login_btn:
        login_btn.click()
    else:
        pass_input.press("Enter")

    # Esperar a que PRTG redirija despues del login
    page.wait_for_load_state("networkidle", timeout=15000)
    print("  Login completado")


def take_screenshot(target_url=None):
    """Captura un screenshot full page de una URL.
    Si no se especifica URL, usa PRTG_URL de la configuracion.
    Retorna los bytes de la imagen PNG."""
    url = target_url or PRTG_URL
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Capturando: {url}")

    with sync_playwright() as p:
        # Lanzar Chromium en modo headless (sin ventana visible)
        # --ignore-certificate-errors: aceptar SSL self-signed de PRTG
        # --no-sandbox: necesario en contenedores Docker Linux
        # --disable-dev-shm-usage: evitar problemas de memoria en Docker
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Crear contexto con viewport y SSL ignorado
        context = browser.new_context(
            viewport={"width": SCREENSHOT_WIDTH, "height": SCREENSHOT_HEIGHT},
            ignore_https_errors=True,
        )
        page = context.new_page()

        try:
            # Login si hay credenciales configuradas
            do_login(page)

            # Navegar a la pagina de PRTG
            print(f"  Navegando a {url}...")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Esperar que la tabla de sensores cargue antes de capturar.
            # PRTG usa diferentes selectores segun la version.
            try:
                page.wait_for_selector("table, .prtgtable, #doareapreview", timeout=10000)
            except Exception:
                print("  WARNING: Selector de tabla no encontrado, capturando como esta")

            # Pausa adicional para que renderice graficos y estilos
            page.wait_for_timeout(2000)

            # Capturar screenshot de toda la pagina (full_page=True)
            screenshot_bytes = page.screenshot(full_page=True, type="png")
            print(f"  OK - {len(screenshot_bytes)} bytes")
            return screenshot_bytes

        except Exception as e:
            print(f"  ERROR - {e}")
            raise
        finally:
            # Cerrar browser siempre, incluso si hay error
            browser.close()


class CaptureHandler(BaseHTTPRequestHandler):
    """Manejador HTTP con dos endpoints:
    GET /capture  - Toma screenshot de PRTG y devuelve PNG
    GET /health   - Health check, retorna OK"""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/capture":
            # Parametro opcional ?url= para capturar otra URL
            params = parse_qs(parsed.query)
            target_url = params.get("url", [None])[0]

            try:
                data = take_screenshot(target_url)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error al capturar: {e}".encode())
                return

            # Responder con la imagen PNG
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        else:
            self.send_response(404)
            self.end_headers()

    # Silenciar logs de cada peticion HTTP (solo muestra los nuestros via print)
    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    # Arrancar servidor HTTP en todas las interfaces
    server = HTTPServer(("0.0.0.0", SERVER_PORT), CaptureHandler)
    print(f"Servidor de captura corriendo en http://0.0.0.0:{SERVER_PORT}/")
    print(f"Endpoint:  GET /capture")
    print(f"Health:    GET /health")
    print(f"PRTG URL:  {PRTG_URL}")
    print(f"Viewport:  {SCREENSHOT_WIDTH}x{SCREENSHOT_HEIGHT}")
    print("Presiona Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        server.server_close()
