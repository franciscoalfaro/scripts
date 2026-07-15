import win32gui, win32ui, win32con
from PIL import Image

hwnd = 67412
left, top, right, bottom = win32gui.GetWindowRect(hwnd)
w = right - left
h = bottom - top
print("Rect: ({},{},{},{}) Size: {}x{}".format(left, top, right, bottom, w, h))

screenDC = win32gui.GetDC(0)
mfcDC = win32ui.CreateDCFromHandle(screenDC)
saveDC = mfcDC.CreateCompatibleDC()

saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitMap)

saveDC.BitBlt((0, 0), (w, h), mfcDC, (left, top), win32con.SRCCOPY)

bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
bw = bmpinfo["bmWidth"]
bh = bmpinfo["bmHeight"]
print("Bitmap: {}x{}".format(bw, bh))

print("Data len: {}".format(len(bmpstr)))
print("Expected: {}".format(bw * bh * 4))
img = Image.frombytes("RGBX", (bw, bh), bmpstr, "raw", "BGRX")
img = img.convert("RGB")
img.save("C:/temp/test_capture.png")
print("Guardado OK: {}x{}".format(img.size[0], img.size[1]))

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(0, screenDC)
print("DONE")
