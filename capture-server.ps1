Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Drawing.Imaging;

public class Win32Capture {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static Bitmap CaptureByHandle(IntPtr hWnd) {
        RECT rect;
        GetWindowRect(hWnd, out rect);
        int w = rect.Right - rect.Left;
        int h = rect.Bottom - rect.Top;
        if (w <= 0 || h <= 0) return null;

        Bitmap bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
        using (Graphics g = Graphics.FromImage(bmp)) {
            IntPtr hdc = g.GetHdc();
            PrintWindow(hWnd, hdc, 2);
            g.ReleaseHdc(hdc);
        }
        return bmp;
    }

    public static Bitmap CaptureFullScreen(int x, int y, int w, int h) {
        Bitmap bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
        using (Graphics g = Graphics.FromImage(bmp)) {
            g.CopyFromScreen(x, y, 0, 0, new Size(w, h));
        }
        return bmp;
    }
}
"@ -ReferencedAssemblies System.Drawing

function Capture-Window {
    param([string]$WindowTitle)

    $proc = Get-Process | Where-Object {
        $_.MainWindowTitle -like "*$WindowTitle*" -and $_.MainWindowHandle -ne [IntPtr]::Zero
    } | Select-Object -First 1

    if (-not $proc) { return $null }

    $hWnd = $proc.MainWindowHandle
    $bmp = [Win32Capture]::CaptureByHandle($hWnd)

    if (-not $bmp) {
        $rect = New-Object Win32Capture+RECT
        [Win32Capture]::GetWindowRect($hWnd, [ref]$rect) | Out-Null
        $w = $rect.Right - $rect.Left
        $h = $rect.Bottom - $rect.Top
        if ($w -gt 0 -and $h -gt 0) {
            $bmp = [Win32Capture]::CaptureFullScreen($rect.Left, $rect.Top, $w, $h)
        }
    }

    return $bmp
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://+:8080/")
$listener.Start()

Write-Host "Servidor de captura corriendo en http://localhost:8080/" -ForegroundColor Green
Write-Host "Endpoint: GET http://localhost:8080/capture?window=Remote%20Desktop%20Manager" -ForegroundColor Cyan
Write-Host "Presiona Ctrl+C para detener" -ForegroundColor Yellow

while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        if ($request.Url.LocalPath -eq "/capture") {
            $windowTitle = $request.QueryString["window"]
            if (-not $windowTitle) { $windowTitle = "Remote Desktop Manager" }

            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Capturando: $windowTitle" -ForegroundColor Gray

            $bmp = Capture-Window -WindowTitle $windowTitle

            if ($bmp) {
                $ms = New-Object System.IO.MemoryStream
                $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
                $bmp.Dispose()
                $bytes = $ms.ToArray()
                $ms.Dispose()

                $response.ContentType = "image/png"
                $response.ContentLength64 = $bytes.Length
                $response.StatusCode = 200
                $response.OutputStream.Write($bytes, 0, $bytes.Length)

                Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OK - $($bytes.Length) bytes" -ForegroundColor Green
            } else {
                $msg = [System.Text.Encoding]::UTF8.GetBytes("Ventana no encontrada: $windowTitle")
                $response.StatusCode = 404
                $response.ContentType = "text/plain"
                $response.ContentLength64 = $msg.Length
                $response.OutputStream.Write($msg, 0, $msg.Length)

                Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ERROR - Ventana no encontrada: $windowTitle" -ForegroundColor Red
            }
        } elseif ($request.Url.LocalPath -eq "/health") {
            $msg = [System.Text.Encoding]::UTF8.GetBytes("OK")
            $response.StatusCode = 200
            $response.ContentType = "text/plain"
            $response.ContentLength64 = $msg.Length
            $response.OutputStream.Write($msg, 0, $msg.Length)
        } else {
            $response.StatusCode = 404
        }

        $response.Close()
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}
