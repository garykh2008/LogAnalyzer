import ctypes
from ctypes import c_int, Structure, POINTER, byref
from ctypes.wintypes import HWND, MSG, RECT
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import QMenuBar, QMainWindow, QApplication, QToolButton, QPushButton, QComboBox, QLineEdit
from PySide6.QtGui import QCursor
import sys

# --- Windows API Constants ---
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_ACTIVATE = 0x0006

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10; HTRIGHT = 11; HTTOP = 12; HTTOPLEFT = 13; HTTOPRIGHT = 14; HTBOTTOM = 15; HTBOTTOMLEFT = 16; HTBOTTOMRIGHT = 17

GWL_STYLE = -16
WS_CAPTION = 0x00C00000; WS_THICKFRAME = 0x00040000; WS_MINIMIZEBOX = 0x00020000; WS_MAXIMIZEBOX = 0x00010000; WS_SYSMENU = 0x00080000
SWP_NOSIZE = 0x0001; SWP_NOMOVE = 0x0002; SWP_FRAMECHANGED = 0x0020

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMSBT_MAINWINDOW = 2 ; DWMWCP_ROUND = 2

class MARGINS(Structure):
    _fields_ = [("cxLeftWidth", c_int), ("cxRightWidth", c_int),
                ("cyTopHeight", c_int), ("cyBottomHeight", c_int)]

dwmapi = ctypes.windll.dwmapi; user32 = ctypes.windll.user32

def is_win11():
    try: return sys.getwindowsversion().build >= 22000
    except: return False

def apply_window_rounding(hwnd_id):
    if not is_win11(): return
    hwnd = HWND(int(hwnd_id))
    corner = c_int(DWMWCP_ROUND)
    dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, byref(corner), ctypes.sizeof(corner))

class NativeWindowMixin:
    """
    Standard Windows 11 Native Window implementation.
    Optimized border width to prevent interference with scrollbars.
    """
    def setup_native_window(self, title_bar_height=40):
        self._title_bar_height = title_bar_height
        self._border_width = 5 # Reduced from 8 to prevent scrollbar interference
        
        if isinstance(self, QMainWindow):
            self.setWindowFlags(self.windowFlags() | Qt.Window)
        
        self.winId() 
        self.refresh_frame()
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        QTimer.singleShot(100, self.refresh_frame)

    def refresh_frame(self):
        if not self.winId(): return
        hwnd = HWND(int(self.winId()))
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
        
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))

    def apply_mica(self, dark_mode=True):
        if not is_win11(): return
        hwnd = HWND(int(self.winId()))
        val = c_int(1 if dark_mode else 0)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(val), ctypes.sizeof(val))
        backdrop = c_int(DWMSBT_MAINWINDOW)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, byref(backdrop), ctypes.sizeof(backdrop))
        corner = c_int(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, byref(corner), ctypes.sizeof(corner))
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)

    def nativeEvent(self, eventType, message):
        if eventType != b"windows_generic_MSG":
            return super().nativeEvent(eventType, message)
        
        msg = ctypes.cast(int(message), POINTER(MSG)).contents
        
        if msg.message == WM_NCCALCSIZE:
            return True, 0
            
        if msg.message == WM_NCHITTEST:
            if isinstance(self, QMainWindow):
                pos = QCursor.pos()
                local_pt = self.mapFromGlobal(pos)
                lx, ly = local_pt.x(), local_pt.y()
                w, h = self.width(), self.height()
                bw = self._border_width
                
                # 1. Resize zones (Precise 5px edge)
                if ly < bw:
                    if lx < bw: return True, HTTOPLEFT
                    if lx > w - bw: return True, HTTOPRIGHT
                    return True, HTTOP
                if ly > h - bw:
                    if lx < bw: return True, HTBOTTOMLEFT
                    if lx > w - bw: return True, HTBOTTOMRIGHT
                    return True, HTBOTTOM
                if lx < bw: return True, HTLEFT
                if lx > w - bw: return True, HTRIGHT
                
                # 2. Title bar / Caption handling
                if ly < self._title_bar_height:
                    target = QApplication.widgetAt(pos)
                    if target:
                        curr = target
                        while curr and curr != self:
                            if isinstance(curr, (QPushButton, QToolButton, QComboBox, QLineEdit, QMenuBar)):
                                if isinstance(curr, QMenuBar):
                                    if curr.actionAt(curr.mapFromGlobal(pos)):
                                        return False, 0
                                    else:
                                        break
                                return False, 0
                            curr = curr.parentWidget()
                    
                    return True, HTCAPTION 
                
                return True, HTCLIENT
            
        return super().nativeEvent(eventType, message)
