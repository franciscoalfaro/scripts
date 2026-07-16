import os
import io
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

PRTG_URL = os.getenv("PRTG_URL", "https://186.10.70.44/sensors.htm?id=0&filter_status=5")
PRTG_LOGIN_URL = os.getenv("PRTG_LOGIN_URL", "https://186.10.70.44/index.htm")
PRTG_USER = os.getenv("PRTG_USER", "")
PRTG_PASS = os.getenv("PRTG_PASS", "")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))
SCREENSHOT_WIDTH = int(os.getenv("SCREENSHOT_WIDTH", "1920"))
SCREENSHOT_HEIGHT = int(os.getenv("SCREENSHOT_HEIGHT", "1080"))


def do_login(page):
    if not PRTG_USER or not PRTG_PASS:
        return

    print(f"  Login en {PRTG_LOGIN_URL}...")
    page.goto(PRTG_LOGIN_URL, wait_until="networkidle", timeout=30000)

    # PRTG login form — intentar selectores comunes
    user_selectors = [
        'input[name="name"]',
        'input[name="username"]',
        'input#name',
        'input[type="text"]',
    ]
    pass_selectors = [
        'input[name="password"]',
        'input[name="pass"]',
        'input#password',
        'input[type="password"]',
    ]
    btn_selectors = [
        'input[type="submit"]',
        'button[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Iniciar")',
        'button:has-text("Sign in")',
        '#loginbutton',
    ]

    user_input = None
    for sel in user_selectors:
        el = page.query_selector(sel)
        if el:
            user_input = el
            break

    pass_input = None
    for sel in pass_selectors:
        el = page.query_selector(sel)
        if el:
            pass_input = el
            break

    login_btn = None
    for sel in btn_selectors:
        el = page.query_selector(sel)
        if el:
            login_btn = el
            break

    if not user_input or not pass_input:
        print("  WARNING: No se encontraron campos de login, continuando sin auth")
        return

    user_input.fill(PRTG_USER)
    pass_input.fill(PRTG_PASS)

    if login_btn:
        login_btn.click()
    else:
        pass_input.press("Enter")

    page.wait_for_load_state("networkidle", timeout=15000)
    print("  Login completado")


def take_screenshot(target_url=None):
    url = target_url or PRTG_URL
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Capturando: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            viewport={"width": SCREENSHOT_WIDTH, "height": SCREENSHOT_HEIGHT},
            ignore_https_errors=True,
        )
        page = context.new_page()

        try:
            do_login(page)

            print(f"  Navegando a {url}...")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Esperar que la tabla de sensores cargue
            try:
                page.wait_for_selector("table, .prtgtable, #doareapreview", timeout=10000)
            except Exception:
                print("  WARNING: Selector de tabla no encontrado, capturando como esta")

            page.wait_for_timeout(2000)

            screenshot_bytes = page.screenshot(full_page=True, type="png")
            print(f"  OK - {len(screenshot_bytes)} bytes")
            return screenshot_bytes

        except Exception as e:
            print(f"  ERROR - {e}")
            raise
        finally:
            browser.close()


class CaptureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/capture":
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

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
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
