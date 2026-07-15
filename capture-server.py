import win32gui
import win32ui
import win32con
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import io
import ctypes
import ctypes.wintypes
import datetime

def find_window(title):
    result = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if title.lower() in window_title.lower():
                result.append((hwnd, window_title))
    win32gui.EnumWindows(callback, None)
    return result[0] if result else None

def capture_window(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    w = right - left
    h = bottom - top
    if w <= 0 or h <= 0:
        print(f"  Dimensiones invalidas: {w}x{h}")
        return None

    # Usar GetDC(0) = pantalla completa y BitBlt de la region
    try:
        screenDC = win32gui.GetDC(0)
        mfcDC = win32ui.CreateDCFromHandle(screenDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # BitBlt copia la region de la pantalla
        saveDC.BitBlt((0, 0), (w, h), mfcDC, (left, top), win32con.SRCCOPY)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        img = Image.frombuffer("RGBX", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX")
        img = img.convert("RGB")

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(0, screenDC)

        return img
    except Exception as e:
        print(f"  BitBlt fallo: {e}")
        try:
            win32gui.ReleaseDC(0, screenDC)
        except:
            pass

    return None

class CaptureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/capture":
            params = parse_qs(parsed.query)
            window_title = params.get("window", ["Remote Desktop Manager"])[0]

            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Capturando: {window_title}")

            match = find_window(window_title)
            if not match:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Ventana no encontrada: {window_title}".encode())
                print(f"  ERROR - Ventana no encontrada")
                return

            hwnd, title = match
            print(f"  Encontrada: {title} (hwnd={hwnd})")
            img = capture_window(hwnd)

            if img is None:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Fallo al capturar la ventana")
                print(f"  ERROR - Fallo al capturar")
                return

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()

            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

            print(f"  OK - {len(data)} bytes")

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
    server = HTTPServer(("0.0.0.0", 8080), CaptureHandler)
    print("Servidor de captura corriendo en http://localhost:8080/")
    print("Endpoint: GET http://localhost:8080/capture?window=Remote%20Desktop%20Manager")
    print("Health:   GET http://localhost:8080/health")
    print("Presiona Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        server.server_close()
