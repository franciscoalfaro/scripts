param(
    [string]$WindowTitle = "PRTG",
    [string]$OutputPath = "C:\temp\capture.png"
)

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

$proc = Get-Process | Where-Object {
    $_.MainWindowTitle -like "*$WindowTitle*" -and $_.MainWindowHandle -ne [IntPtr]::Zero
} | Select-Object -First 1

if (-not $proc) {
    Write-Error "No se encontro ventana con titulo: $WindowTitle"
    exit 1
}

$hWnd = $proc.MainWindowHandle
[Console]::Error.WriteLine("Ventana: $($proc.MainWindowTitle) (PID: $($proc.Id))")

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

if (-not $bmp) {
    Write-Error "No se pudo capturar la ventana"
    exit 1
}

$bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

[Console]::Error.WriteLine("Captura guardada en: $OutputPath")

$bytes = [System.IO.File]::ReadAllBytes($OutputPath)
$base64 = [Convert]::ToBase64String($bytes)
Write-Output $base64
