import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
import time
import os
import sys
import io
import ctypes
import ctypes.wintypes
import shutil
import queue
import datetime
import json
import logging

logging.basicConfig(
    filename='tool_htth.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logging.info("=========================================")
logging.info("AutoGame Tool Khoi Dong")

# --- CẤU HÌNH DPI ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- FIX UNICODE ---
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except Exception:
    pass

# --- IMPORT WIN32 ---
try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt pywin32:\npip install pywin32")
    sys.exit()

# --- IMPORT PYNPUT ---
try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button
    from pynput.keyboard import Key
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Loi: pip install pynput")

# --- IMPORT PYDIRECTINPUT (Hardware Mouse) ---
try:
    import pydirectinput
    pydirectinput.PAUSE = 0.01  # Giảm độ trễ
    DIRECTINPUT_AVAILABLE = True
except ImportError:
    DIRECTINPUT_AVAILABLE = False
    print("Loi: pip install pydirectinput")


# =========================
# SENDINPUT STRUCTURES
# =========================
INPUT_MOUSE           = 0
MOUSEEVENTF_MOVE      = 0x0001
MOUSEEVENTF_LEFTDOWN  = 0x0002
MOUSEEVENTF_LEFTUP    = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010
MOUSEEVENTF_WHEEL     = 0x0800
MOUSEEVENTF_ABSOLUTE  = 0x8000

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT_UNION)]


# =========================
# CÁC PHƯƠNG THỨC CLICK + ENTER
# =========================

def get_real_child_hwnd(parent_hwnd, x, y):
    """Tự động luồn sâu vào các Child Window tại tọa độ x, y và dịch tọa độ tương ứng"""
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    
    curr_hwnd = parent_hwnd
    curr_x, curr_y = x, y
    
    for _ in range(5): 
        pt = POINT(curr_x, curr_y)
        child = ctypes.windll.user32.ChildWindowFromPoint(curr_hwnd, pt)
        
        if not child or child == curr_hwnd:
            break
            
        s_pt = POINT(curr_x, curr_y)
        ctypes.windll.user32.ClientToScreen(curr_hwnd, ctypes.byref(s_pt))
        ctypes.windll.user32.ScreenToClient(child, ctypes.byref(s_pt))
        
        curr_x, curr_y = s_pt.x, s_pt.y
        curr_hwnd = child
        
    return curr_hwnd, curr_x, curr_y


def send_click_sendinput(hwnd, x, y, button="left"):
    try:
        # Cập nhật HWND và tọa độ thực tế đề phòng Child Window
        hwnd, x, y = get_real_child_hwnd(hwnd, x, y)
        
        # SendInput cần tọa độ màn hình Absolute
        rect = win32gui.GetWindowRect(hwnd)
        screen_x = rect[0] + x
        screen_y = rect[1] + y
        sm_cx = ctypes.windll.user32.GetSystemMetrics(0)
        sm_cy = ctypes.windll.user32.GetSystemMetrics(1)
        abs_x = int(screen_x * 65535 / sm_cx)
        abs_y = int(screen_y * 65535 / sm_cy)
        
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.02)

        def make_input(flags):
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp._input.mi.dwFlags = flags | MOUSEEVENTF_ABSOLUTE
            inp._input.mi.dx = abs_x
            inp._input.mi.dy = abs_y
            return inp

        down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        up_flag   = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP

        inputs = (INPUT * 3)(
            make_input(MOUSEEVENTF_MOVE),
            make_input(down_flag),
            make_input(up_flag),
        )
        ctypes.windll.user32.SendInput(3, inputs, ctypes.sizeof(INPUT))
    except Exception as e:
        print(f"[SendInput] loi: {e}")


def send_key_enter(hwnd):
    try:
        vk   = 0x0D
        scan = win32api.MapVirtualKey(vk, 0)
        lp_down = (scan << 16) | 1
        lp_up   = (scan << 16) | 1 | (1 << 30) | (1 << 31)
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lp_down)
        time.sleep(0.015)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, lp_up)
    except Exception as e:
        print(f"[Enter] loi: {e}")


# =========================
# BROADCAST WORKER
# =========================
class BroadcastWorker:
    def __init__(self):
        self.q = queue.Queue(maxsize=200)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                task = self.q.get(timeout=1)
                if task is None:
                    break
                fn, args = task
                fn(*args)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Worker] {e}")

    def submit(self, fn, *args):
        try:
            self.q.put_nowait((fn, args))
        except queue.Full:
            pass

    def stop(self):
        self.q.put(None)


# =========================
# SHELLEXECUTE
# =========================
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1

class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize",         ctypes.c_ulong),
        ("fMask",          ctypes.c_ulong),
        ("hwnd",           ctypes.c_void_p),
        ("lpVerb",         ctypes.c_wchar_p),
        ("lpFile",         ctypes.c_wchar_p),
        ("lpParameters",   ctypes.c_wchar_p),
        ("lpDirectory",    ctypes.c_wchar_p),
        ("nShow",          ctypes.c_int),
        ("hInstApp",       ctypes.c_void_p),
        ("lpIDList",       ctypes.c_void_p),
        ("lpClass",        ctypes.c_wchar_p),
        ("hkeyClass",      ctypes.c_void_p),
        ("dwHotKey",       ctypes.c_ulong),
        ("hIconOrMonitor", ctypes.c_void_p),
        ("hProcess",       ctypes.c_void_p),
    ]

def shell_open_with_pid(filepath, work_dir=None):
    sei = SHELLEXECUTEINFO()
    sei.cbSize       = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask        = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd         = None
    sei.lpVerb       = "open"
    sei.lpFile       = filepath
    sei.lpParameters = None
    sei.lpDirectory  = work_dir or os.path.dirname(filepath)
    sei.nShow        = SW_SHOWNORMAL
    ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
    if not ok:
        raise ctypes.WinError()
    hproc = sei.hProcess
    pid = None
    if hproc:
        try:
            pid = ctypes.windll.kernel32.GetProcessId(ctypes.c_void_p(hproc))
        except Exception:
            pid = None
    return pid, hproc


class WinProcWrapper:
    def __init__(self, pid=None, hprocess=None):
        self.pid      = pid
        self.hprocess = hprocess

    def poll(self):
        if not self.hprocess:
            return None
        try:
            ret = ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_void_p(self.hprocess), 0)
            return None if ret == 0x00000102 else 0
        except Exception:
            return None

    def terminate(self):
        if self.hprocess:
            try:
                ctypes.windll.kernel32.TerminateProcess(ctypes.c_void_p(self.hprocess), 1)
            except Exception:
                pass

    def close_handle(self):
        if self.hprocess:
            try:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self.hprocess))
            except Exception:
                pass
            self.hprocess = None


# =========================
# SCROLLABLE FRAME (game area)
# =========================
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg="#202020", highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical",   command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        ttk.Style().configure("Black.TFrame", background="#202020")
        self.scrollable_frame = ttk.Frame(self.canvas, style="Black.TFrame")

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_yscroll,
                               xscrollcommand=self._on_xscroll)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.canvas.bind_all("<Shift-MouseWheel>",
            lambda e: self.canvas.xview_scroll(int(-1*(e.delta/120)), "units"))

        self._vsb_visible = False
        self._hsb_visible = False

    def _on_yscroll(self, first, last):
        first, last = float(first), float(last)
        if first <= 0.0 and last >= 1.0:
            if self._vsb_visible:
                self.vsb.grid_remove()
                self._vsb_visible = False
        else:
            if not self._vsb_visible:
                self.vsb.grid(row=0, column=1, sticky="ns")
                self._vsb_visible = True
        self.vsb.set(first, last)

    def _on_xscroll(self, first, last):
        first, last = float(first), float(last)
        if first <= 0.0 and last >= 1.0:
            if self._hsb_visible:
                self.hsb.grid_remove()
                self._hsb_visible = False
        else:
            if not self._hsb_visible:
                self.hsb.grid(row=1, column=0, sticky="ew")
                self._hsb_visible = True
        self.hsb.set(first, last)


# =========================
# CLICK MODE MAP
# =========================
CLICK_MODES = {
    "SendInput    (Win32 API - Hardware)": "input",
    "DirectInput  (Gia lap chuot that)":   "direct",
}


# =========================
# QUICK BUTTON ITEM
# =========================
class QuickButtonItem:
    def __init__(self, parent_frame, manager, idx):
        self.manager = manager
        self.idx     = idx
        self._stop_event = threading.Event()
        self._running    = False
        self._thread     = None
        self._click_count = 0
        self._picking           = False
        self._pick_key_listener = None

        BG = "#eaeaea"

        self.frame = tk.Frame(parent_frame, bg=BG, relief="groove", bd=2)
        self.frame.pack(fill=tk.X, pady=3, padx=3)

        hdr = tk.Frame(self.frame, bg="#3a5f8a")
        hdr.pack(fill=tk.X)

        self.lbl_idx = tk.Label(hdr, text=f" Nút #{idx} ", bg="#3a5f8a", fg="white",
                                 font=("Arial", 8, "bold"))
        self.lbl_idx.pack(side=tk.LEFT, padx=4, pady=2)

        self.lbl_status = tk.Label(hdr, text="Chờ", fg="#aad4ff",
                                    bg="#3a5f8a", font=("Arial", 7))
        self.lbl_status.pack(side=tk.RIGHT, padx=6, pady=2)

        row1 = tk.Frame(self.frame, bg=BG)
        row1.pack(fill=tk.X, padx=4, pady=(4,1))

        tk.Label(row1, text="X:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.x_var = tk.StringVar(value="160")
        tk.Entry(row1, textvariable=self.x_var, width=4, justify="center",
                 font=("Arial",8)).pack(side=tk.LEFT, padx=(1,2))

        tk.Label(row1, text="Y:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.y_var = tk.StringVar(value="225")
        tk.Entry(row1, textvariable=self.y_var, width=4, justify="center",
                 font=("Arial",8)).pack(side=tk.LEFT, padx=(1,2))

        self.pick_btn = tk.Button(
            row1, text="🎯", bg="#e67e22", fg="white",
            font=("Arial", 8), relief="flat", padx=3, pady=0,
            command=self._toggle_pick
        )
        self.pick_btn.pack(side=tk.LEFT, padx=(1,4))

        tk.Label(row1, text="Loại:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.btn_var = tk.StringVar(value="Trái")
        ttk.Combobox(row1, textvariable=self.btn_var,
                     values=["Trái", "Phải", "Enter"],
                     state="readonly", width=6,
                     font=("Arial",8)).pack(side=tk.LEFT, padx=(1,0))

        row2 = tk.Frame(self.frame, bg=BG)
        row2.pack(fill=tk.X, padx=4, pady=1)

        tk.Label(row2, text="Ms:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="500")
        tk.Entry(row2, textvariable=self.interval_var, width=5, justify="center",
                 font=("Arial",8)).pack(side=tk.LEFT, padx=(1,4))

        tk.Label(row2, text="Lặp:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.count_var = tk.StringVar(value="0")
        tk.Entry(row2, textvariable=self.count_var, width=4, justify="center",
                 font=("Arial",8)).pack(side=tk.LEFT, padx=(1,2))
        tk.Label(row2, text="(0=∞)", bg=BG, font=("Arial",7), fg="gray").pack(side=tk.LEFT)

        row3 = tk.Frame(self.frame, bg=BG)
        row3.pack(fill=tk.X, padx=4, pady=1)

        tk.Label(row3, text="Gửi đến:", bg=BG, font=("Arial",8)).pack(side=tk.LEFT)
        self.target_var = tk.StringVar(value="all")
        self.target_combo = ttk.Combobox(
            row3, textvariable=self.target_var,
            values=["all"],
            state="readonly", width=9,
            font=("Arial",8),
            postcommand=self._refresh_targets_cb
        )
        self.target_combo.pack(side=tk.LEFT, padx=(3,0))

        row4 = tk.Frame(self.frame, bg=BG)
        row4.pack(fill=tk.X, padx=4, pady=(2,5))

        self.btn_start = tk.Button(
            row4, text="▶ Bắt đầu", bg="#27ae60", fg="white",
            font=("Arial",8,"bold"), relief="flat", padx=4,
            command=self.start
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0,3))

        self.btn_stop = tk.Button(
            row4, text="⏹ Dừng", bg="#c0392b", fg="white",
            font=("Arial",8,"bold"), relief="flat", padx=4,
            state="disabled", command=self.stop
        )
        self.btn_stop.pack(side=tk.LEFT)

    def set_index(self, idx):
        self.idx = idx
        self.lbl_idx.config(text=f" Nút #{idx} ")

    def _refresh_targets_cb(self):
        ids     = sorted(self.manager.running_instances.keys())
        options = ["all"] + [f"G{i}" for i in ids]
        self.target_combo["values"] = options
        if self.target_var.get() not in options:
            self.target_var.set("all")

    def _get_targets(self):
        mode = self.target_var.get()
        ids  = sorted(self.manager.running_instances.keys())
        if mode == "all":
            return ids
        elif mode.startswith("G"):
            try:
                iid = int(mode[1:])
                return [iid] if iid in self.manager.running_instances else ids
            except ValueError:
                return ids
        return ids

    def _toggle_pick(self):
        if self._picking:
            self._stop_pick()
        else:
            self._start_pick()

    def _start_pick(self):
        if self._picking:
            return
        self._picking = True
        try:
            self.pick_btn.config(bg="#c0392b", text="🔒")
            self.lbl_status.config(text="Rê chuột → F2 khóa", fg="#e67e22")
        except Exception:
            pass
        self._pick_poll()
        if PYNPUT_AVAILABLE:
            def _on_key(k):
                try:
                    if k == Key.f2:
                        self.manager.root.after(0, self._stop_pick)
                except Exception:
                    pass
            self._pick_key_listener = keyboard.Listener(on_press=_on_key)
            self._pick_key_listener.daemon = True
            self._pick_key_listener.start()

    def _pick_poll(self):
        if not self._picking:
            return

        class _PT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        try:
            pt = _PT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            for iid in sorted(self.manager.running_instances.keys()):
                d = self.manager.running_instances.get(iid)
                c = d.get("container") if d else None
                if not c: continue
                try:
                    rx = c.winfo_rootx(); ry = c.winfo_rooty()
                    rw = c.winfo_width(); rh = c.winfo_height()
                    if rx <= pt.x <= rx + rw and ry <= pt.y <= ry + rh:
                        self.x_var.set(str(pt.x - rx))
                        self.y_var.set(str(pt.y - ry))
                        break
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.manager.root.after(50, self._pick_poll)
        except Exception:
            pass

    def _stop_pick(self):
        self._picking = False
        if self._pick_key_listener:
            try:
                self._pick_key_listener.stop()
            except Exception:
                pass
            self._pick_key_listener = None
        try:
            self.pick_btn.config(bg="#e67e22", text="🎯")
            self.lbl_status.config(
                text=f"Khoa ({self.x_var.get()},{self.y_var.get()})",
                fg="#27ae60"
            )
        except Exception:
            pass

    def _do_one_click(self, targets):
        btn_type = self.btn_var.get()
        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
        except ValueError:
            return
        
        mode = self.manager.click_mode

        for iid in targets:
            d    = self.manager.running_instances.get(iid)
            hwnd = d.get("hwnd") if d else None
            container = d.get("container") if d else None
            
            if not hwnd:
                continue
                
            if btn_type == "Enter":
                send_key_enter(hwnd)
            else:
                btn_str = "left" if btn_type == "Trai" else "right"
                
                if mode == "direct":
                    if container and DIRECTINPUT_AVAILABLE:
                        try:
                            # 1. Focus cửa sổ chứa game lên
                            win32gui.SetForegroundWindow(self.manager.root.winfo_id())
                            # 2. Tính tọa độ tuyệt đối trên toàn bộ màn hình
                            abs_x = container.winfo_rootx() + x
                            abs_y = container.winfo_rooty() + y
                            # 3. Kéo chuột thật tới đó và click
                            pydirectinput.moveTo(abs_x, abs_y)
                            if btn_str == "left":
                                pydirectinput.click()
                            else:
                                pydirectinput.rightClick()
                        except Exception as e:
                            print(f"[DirectInput] Loi: {e}")
                else:
                    # mode == "input"
                    send_click_sendinput(hwnd, x, y, btn_str)

    def _set_status(self, text, color="gray"):
        try:
            self.manager.root.after(0, lambda: self.lbl_status.config(text=text, fg=color))
        except Exception:
            pass

    def _worker(self):
        try:
            interval = max(50, int(self.interval_var.get())) / 1000.0
        except ValueError:
            interval = 0.5
        try:
            count = int(self.count_var.get())
        except ValueError:
            count = 0

        self._click_count = 0
        btn_label = self.btn_var.get()

        while not self._stop_event.is_set():
            if count > 0 and self._click_count >= count:
                break
            targets = self._get_targets()
            if not targets:
                self._set_status("No taq!", "red")
                break
            self._do_one_click(targets)
            self._click_count += 1
            suffix = f"/{count}" if count > 0 else "/∞"
            self._set_status(f"⚡{btn_label} x{self._click_count}{suffix}", "#1abc9c")
            self._stop_event.wait(interval)

        total = self._click_count
        self._running = False

        def _done():
            try:
                self.lbl_status.config(text=f"OK {total}x", fg="#555")
                self.btn_start.config(state="normal")
                self.btn_stop.config(state="disabled")
            except Exception:
                pass
        try:
            self.manager.root.after(0, _done)
        except Exception:
            pass

    def start(self):
        if self._running:
            return
        if not self.manager.running_instances:
            messagebox.showwarning("Thong bao", "Chua co taq nao dang mo.")
            return
        self._stop_event.clear()
        self._running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="Dang chay...", fg="#2980b9")
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._running = False
        try:
            self.lbl_status.config(text="Dung", fg="#888")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
        except Exception:
            pass

    def destroy_item(self):
        self.stop()
        self._picking = False
        if self._pick_key_listener:
            try:
                self._pick_key_listener.stop()
            except Exception:
                pass
            self._pick_key_listener = None
        try:
            self.frame.destroy()
        except Exception:
            pass


# =========================
# QUICK BUTTONS PANEL (panel trai)
# =========================
class QuickButtonsPanel:
    def __init__(self, parent, manager):
        self.manager = manager
        self.buttons  = []

        DARK  = "#2c3e50"
        MID   = "#34495e"
        LIGHT = "#ecf0f1"

        self.outer = tk.Frame(parent, width=235, bg=DARK)
        self.outer.pack(side=tk.LEFT, fill=tk.Y)
        self.outer.pack_propagate(False)

        hdr = tk.Frame(self.outer, bg=DARK)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⚡ QUICK AUTO CLICK",
                 bg=DARK, fg="#f1c40f",
                 font=("Arial", 9, "bold")).pack(pady=6)

        bar = tk.Frame(self.outer, bg=MID)
        bar.pack(fill=tk.X)

        btn_cfg = dict(font=("Arial",9,"bold"), relief="flat", bd=0, pady=3, padx=6)

        tk.Button(bar, text=" + ", bg="#27ae60", fg="white",
                  command=self.add_button, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(bar, text=" − ", bg="#e74c3c", fg="white",
                  command=self.remove_last, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=2)

        tk.Button(bar, text="▶ Tất cả", bg="#2980b9", fg="white",
                  command=self.start_all, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(bar, text="⏹ Dừng", bg="#8e44ad", fg="white",
                  command=self.stop_all, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=2)

        self.lbl_count = tk.Label(bar, text="0 nút", bg=MID, fg="#bdc3c7",
                                   font=("Arial",7))
        self.lbl_count.pack(side=tk.RIGHT, padx=6)

        scroll_wrap = tk.Frame(self.outer, bg=LIGHT)
        scroll_wrap.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(scroll_wrap, bg=LIGHT, highlightthickness=0)
        self._vsb    = ttk.Scrollbar(scroll_wrap, orient="vertical",
                                      command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = tk.Frame(self._canvas, bg=LIGHT)
        self._win_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_cfg)
        self._canvas.bind("<Configure>", self._on_canvas_cfg)

        for widget in (self._canvas, self._inner, scroll_wrap):
            widget.bind("<MouseWheel>", self._on_wheel)

        self.add_button()

    def _on_inner_cfg(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_cfg(self, e):
        self._canvas.itemconfig(self._win_id, width=e.width)

    def _on_wheel(self, e):
        self._canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    def _reindex(self):
        for i, btn in enumerate(self.buttons):
            btn.set_index(i + 1)
        self.lbl_count.config(text=f"{len(self.buttons)} nut")

    def add_button(self):
        idx  = len(self.buttons) + 1
        item = QuickButtonItem(self._inner, self.manager, idx)
        for w in (item.frame,):
            w.bind("<MouseWheel>", self._on_wheel)
        self.buttons.append(item)
        self._reindex()

    def remove_last(self):
        if not self.buttons:
            return
        last = self.buttons.pop()
        last.destroy_item()
        self._reindex()

    def stop_all(self):
        for b in self.buttons:
            b.stop()

    def start_all(self):
        for b in self.buttons:
            if not b._running:
                b.start()

    def destroy_all(self):
        for b in self.buttons:
            b.stop()
        self.buttons.clear()

    # def _do_send_single_key(self, iid, vk, down, key_obj):
    #     """Hàm ép gửi phím vào 1 tab cụ thể để chơi tay độc lập"""
    #     scan = win32api.MapVirtualKey(vk, 0)
    #     lp   = (scan << 16) | 1
    #     if key_obj in [Key.up, Key.down, Key.left, Key.right]:
    #         lp |= (1 << 24)
    #     msg = win32con.WM_KEYDOWN if down else win32con.WM_KEYUP
    #     if not down:
    #         lp |= (1 << 30) | (1 << 31)
            
    #     d = self.manager.running_instances.get(iid)
    #     hwnd = d.get("hwnd") if d else None
    #     if hwnd:
    #         try: win32api.PostMessage(hwnd, msg, vk, lp)
    #         except Exception: pass
# =========================
# MAIN APP
# =========================
class TapGameManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Game V20 - DirectInput + SendInput Only")
        self.root.geometry("1680x920")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.base_dir = self._get_base_dir()
        self.game_dir = os.path.join(self.base_dir, "game")

        self.running_instances        = {}
        self.instance_counter         = 0
        self.embedded_hwnds           = []
        self.resize_timer             = None
        self.available_games          = {}
        self.current_file_path        = None
        self.custom_game_key          = None
        self.is_master_mouse_running  = False
        self.is_master_rmouse_running = False
        self.is_master_scroll_running = False
        self.is_master_key_running    = False
        self.last_lclick_time         = 0
        self.last_rclick_time         = 0
        self.click_mode               = "input"
        self._master_bounds           = None

        self.broadcaster = BroadcastWorker()

        self.auto_click_running     = False
        self._auto_click_stop_event = threading.Event()
        self._auto_click_thread     = None

        self.setup_ui()
        self.load_accounts()
        self.scan_game_files()

        if not PYNPUT_AVAILABLE:
            self.master_mouse_var.set(False)
            self.master_key_var.set(False)
        else:
            self.start_input_listeners()

        self.game_area.bind("<Configure>", self.on_window_resize)
        self._update_master_bounds()

    @staticmethod
    def _get_base_dir():
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _update_master_bounds(self):
        try:
            master = self.running_instances.get(1)
            if master and master.get("container"):
                c = master["container"]
                x = c.winfo_rootx(); y = c.winfo_rooty()
                w = c.winfo_width(); h = c.winfo_height()
                if w > 100 and h > 100:
                    self._master_bounds = (x, y, w, h)
                else:
                    self._master_bounds = None
            else:
                self._master_bounds = None
        except Exception:
            self._master_bounds = None
        self.root.after(100, self._update_master_bounds)

    # ==========================================================
    # UI SETUP
    # ==========================================================
    def setup_ui(self):
        self.quick_panel = QuickButtonsPanel(self.root, self)

        self.game_area = tk.Frame(self.root, bg="#202020")
        self.game_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.game_container = ScrollableFrame(self.game_area)
        self.game_container.pack(fill=tk.BOTH, expand=True)
        self.game_grid = self.game_container.scrollable_frame

        sidebar_wrap = tk.Frame(self.root, width=365, bg="#f0f0f0")
        sidebar_wrap.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_wrap.pack_propagate(False)

        sb_canvas = tk.Canvas(sidebar_wrap, bg="#f0f0f0", highlightthickness=0)
        sb_vsb    = ttk.Scrollbar(sidebar_wrap, orient="vertical", command=sb_canvas.yview)
        sb_canvas.configure(yscrollcommand=sb_vsb.set)
        sb_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        sb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(sb_canvas, bg="#f0f0f0", padx=8, pady=6)
        _sb_win = sb_canvas.create_window((0, 0), window=self.sidebar, anchor="nw")
        self.sidebar.bind("<Configure>",
            lambda e: sb_canvas.configure(scrollregion=sb_canvas.bbox("all")))
        sb_canvas.bind("<Configure>",
            lambda e: sb_canvas.itemconfig(_sb_win, width=e.width))

        def _sb_wheel(e):
            try:
                wx = sb_canvas.winfo_rootx(); wy = sb_canvas.winfo_rooty()
                ww = sb_canvas.winfo_width(); wh = sb_canvas.winfo_height()
                if wx <= e.x_root <= wx+ww and wy <= e.y_root <= wy+wh:
                    sb_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        sb_canvas.bind_all("<MouseWheel>", _sb_wheel)

        sp = self.sidebar

        g1 = ttk.LabelFrame(sp, text="1. Chọn File Chạy", padding=8)
        g1.pack(fill=tk.X, pady=(4, 10))

        ttk.Label(g1, text="File trong thư mục game/:").pack(anchor="w")
        self.game_select_var = tk.StringVar()
        self.game_combo = ttk.Combobox(g1, textvariable=self.game_select_var, state="readonly")
        self.game_combo.pack(fill=tk.X, pady=3)
        self.game_combo.bind("<<ComboboxSelected>>", self.on_game_selected)

        bf = ttk.Frame(g1); bf.pack(fill=tk.X, pady=(5, 3))
        ttk.Button(bf, text="Quét lại",    command=self.scan_game_files).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bf, text="Chọn file...", command=self.browse_game_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4,0))

        self.lbl_info = tk.Label(g1, text="[Chưa có file]", fg="blue", wraplength=330, justify="left")
        self.lbl_info.pack(anchor="w", pady=5)

        fq = ttk.Frame(g1); fq.pack(fill=tk.X, pady=3)
        ttk.Label(fq, text="Số lượng:").pack(side=tk.LEFT)
        ttk.Button(fq, text="-", width=3, command=self.decrease_qty).pack(side=tk.LEFT, padx=(4,0))
        self.qty_entry = ttk.Entry(fq, width=5, justify='center')
        self.qty_entry.insert(0, "1"); self.qty_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(fq, text="+", width=3, command=self.increase_qty).pack(side=tk.LEFT)

        ttk.Label(g1, text="Tên cửa sổ game (Để trống tự auto-detect):").pack(anchor="w", pady=(8,2))
        self.title_entry = ttk.Entry(g1)
        self.title_entry.insert(0, "AngelChip"); self.title_entry.pack(fill=tk.X)

        g2 = ttk.LabelFrame(sp, text="2. Kích Thước", padding=8)
        g2.pack(fill=tk.X, pady=(0, 10))
        fs = ttk.Frame(g2); fs.pack(fill=tk.X)
        ttk.Label(fs, text="Rộng:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(fs, width=6)
        self.width_entry.insert(0, "260"); self.width_entry.pack(side=tk.LEFT, padx=(4, 15))
        ttk.Label(fs, text="Cao:").pack(side=tk.LEFT)
        self.height_entry = ttk.Entry(fs, width=6)
        self.height_entry.insert(0, "340"); self.height_entry.pack(side=tk.LEFT, padx=(4, 0))

        btn_run = tk.Button(sp, text="CHẠY NGAY", font=("Arial", 10, "bold"), bg="#4CAF50", fg="white", command=self.start_game_instances)
        btn_run.pack(fill=tk.X, pady=(0, 4), ipady=5)
        
        btn_stop = tk.Button(sp, text="ĐÓNG HẾT", font=("Arial", 10, "bold"), bg="#f44336", fg="white", command=self.stop_all_instances)
        btn_stop.pack(fill=tk.X, pady=(0, 4), ipady=5)
        
        btn_acc = tk.Button(sp, text="QUẢN LÝ TÀI KHOẢN", font=("Arial", 10, "bold"), bg="#2196F3", fg="white", command=self.open_account_manager)
        btn_acc.pack(fill=tk.X, pady=(0, 10), ipady=5)

        g3 = ttk.LabelFrame(sp, text="3. Tắt Theo Range", padding=8)
        g3.pack(fill=tk.X, pady=(0, 10))
        rr = ttk.Frame(g3); rr.pack(fill=tk.X, pady=3)
        ttk.Label(rr, text="Tu:").pack(side=tk.LEFT)
        self.close_from_var = tk.StringVar(value="1")
        self.close_from_combo = ttk.Combobox(rr, textvariable=self.close_from_var, state="readonly", width=6)
        self.close_from_combo.pack(side=tk.LEFT, padx=4)
        ttk.Label(rr, text="Den:").pack(side=tk.LEFT, padx=(8,0))
        self.close_to_var = tk.StringVar(value="1")
        self.close_to_combo = ttk.Combobox(rr, textvariable=self.close_to_var, state="readonly", width=6)
        self.close_to_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(g3, text="TAT THEO RANGE", command=self.close_range_instances).pack(fill=tk.X, pady=4)
        self.lbl_range_info = tk.Label(g3, text="Chua co taq", fg="gray", wraplength=330, justify="left")
        self.lbl_range_info.pack(anchor="w")

        g4 = ttk.LabelFrame(sp, text="4. Dong Bo (Mirror)", padding=8)
        g4.pack(fill=tk.X, pady=4)

        self.master_mouse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Link Chuot Trai", variable=self.master_mouse_var, command=self.toggle_modes).pack(anchor="w")
        self.master_rmouse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Link Chuot Phai", variable=self.master_rmouse_var, command=self.toggle_modes).pack(anchor="w")
        self.master_scroll_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Link Cuon (Scroll)", variable=self.master_scroll_var, command=self.toggle_modes).pack(anchor="w")
        self.master_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Link Phim", variable=self.master_key_var, command=self.toggle_modes).pack(anchor="w")

        fd = ttk.Frame(g4); fd.pack(fill=tk.X, pady=(5,0))
        ttk.Label(fd, text="Delay giua taq (ms):").pack(side=tk.LEFT)
        self.sync_delay_var = tk.IntVar(value=0)
        ttk.Spinbox(fd, from_=0, to=500, increment=10,
                    textvariable=self.sync_delay_var, width=6).pack(side=tk.LEFT, padx=4)

        ttk.Separator(g4, orient="horizontal").pack(fill=tk.X, pady=6)
        ttk.Label(g4, text="Phuong thuc click:", font=("Arial",9,"bold")).pack(anchor="w")

        self.click_mode_var = tk.StringVar(value=list(CLICK_MODES.keys())[0])
        for label in CLICK_MODES:
            ttk.Radiobutton(g4, text=label, variable=self.click_mode_var, value=label,
                            command=self.on_click_mode_changed).pack(anchor="w", pady=1)

    def on_click_mode_changed(self):
        label = self.click_mode_var.get()
        self.click_mode = CLICK_MODES.get(label, "input")

    # ==========================================================
    # RANGE
    # ==========================================================
    def get_open_instance_ids(self):
        return sorted(self.running_instances.keys())

    def update_close_range_ui(self):
        ids = self.get_open_instance_ids()
        if ids:
            vals = [str(i) for i in ids]
            self.close_from_combo["values"] = vals
            self.close_to_combo["values"]   = vals
            if self.close_from_var.get() not in vals: self.close_from_var.set(vals[0])
            if self.close_to_var.get()   not in vals: self.close_to_var.set(vals[-1])
            self.lbl_range_info.config(
                text=f"Dang mo: {len(ids)} taq | ID: {', '.join(vals)}", fg="green")
        else:
            self.close_from_combo["values"] = []
            self.close_to_combo["values"]   = []
            self.close_from_var.set("")
            self.close_to_var.set("")
            self.lbl_range_info.config(text="Chua co taq dang mo", fg="gray")

    def close_range_instances(self):
        ids = self.get_open_instance_ids()
        if not ids:
            messagebox.showwarning("Thong bao", "Hien chua co taq nao dang mo.")
            return
        vf = self.close_from_var.get().strip()
        vt = self.close_to_var.get().strip()
        if not vf or not vt:
            messagebox.showwarning("Thieu du lieu", "Hay chon khoang taq can tat.")
            return
        try:
            s, e = int(vf), int(vt)
        except ValueError:
            messagebox.showwarning("Loi", "Gia tri range khong hop le.")
            return
        if s > e: s, e = e, s
        targets = [i for i in ids if s <= i <= e]
        if not targets:
            messagebox.showwarning("Khong co taq", f"Khong co taq nao trong khoang {s}→{e}.")
            return
        if not messagebox.askyesno("Xac nhan", f"Tat: {', '.join('G'+str(i) for i in targets)}?"):
            return
        for iid in targets:
            self.close_one_instance(iid)
        self.rearrange_layout()
        self.update_close_range_ui()

    # ==========================================================
    # SCAN / BROWSE
    # ==========================================================
    def scan_game_files(self):
        old = self.current_file_path
        self.available_games.clear()
        os.makedirs(self.game_dir, exist_ok=True)
        found = []
        
        # Quet thu muc goc (base_dir) nhung chi lay file (khong vao thu muc con de tranh lag)
        try:
            for name in os.listdir(self.base_dir):
                fp = os.path.join(self.base_dir, name)
                if os.path.isfile(fp) and name.lower().endswith((".exe",".jar",".bat",".cmd")):
                    found.append((f"[Root] {name}", fp))
        except Exception:
            pass

        # Quet thu muc game_dir (co the vao thu muc con)
        for rd, _, files in os.walk(self.game_dir):
            for name in files:
                if name.lower().endswith((".exe",".jar",".bat",".cmd")):
                    fp = os.path.abspath(os.path.join(rd, name))
                    found.append((f"[Game] {os.path.relpath(fp, self.game_dir)}", fp))
                    
        found.sort(key=lambda x: x[0].lower())
        for rel, fp in found:
            self.available_games[rel.replace("\\", " / ")] = fp

        if old and os.path.isfile(old):
            norm_old = os.path.normcase(os.path.abspath(old))
            if not any(os.path.normcase(os.path.abspath(v)) == norm_old
                       for v in self.available_games.values()):
                key = f"[Browse] {os.path.basename(old)}"
                self.available_games[key] = old

        names = list(self.available_games.keys())
        self.game_combo["values"] = names
        if names:
            sel = None
            if old and os.path.isfile(old):
                norm_old = os.path.normcase(os.path.abspath(old))
                sel = next((k for k,v in self.available_games.items()
                            if os.path.normcase(os.path.abspath(v)) == norm_old), None)
            if not sel:
                sel = next((n for n in names if "angelchip" in n.lower()), names[0])
            self.game_select_var.set(sel)
            self.current_file_path = self.available_games[sel]
            self.update_file_info()
        else:
            self.game_select_var.set("")
            self.current_file_path = None
            self.lbl_info.config(text=f"Khong tim thay file trong:\n{self.game_dir}", fg="red")

    def on_game_selected(self, event=None):
        name = self.game_select_var.get().strip()
        path = self.available_games.get(name)
        if path and os.path.isfile(path):
            self.current_file_path = os.path.abspath(path)
            self.update_file_info()
        else:
            self.current_file_path = None
            self.lbl_info.config(text="[File khong con ton tai]", fg="red")

    def browse_game_file(self):
        os.makedirs(self.game_dir, exist_ok=True)
        file = filedialog.askopenfilename(
            title="Chon file game", initialdir=self.game_dir,
            filetypes=[("Game files",("*.exe","*.jar","*.bat","*.cmd")),("All files","*.*")]
        )
        if not file: return
        file = os.path.abspath(file)
        if not os.path.isfile(file):
            messagebox.showerror("Loi", f"File khong ton tai:\n{file}"); return
        norm = os.path.normcase(file)
        ek = next((k for k,v in self.available_games.items()
                   if os.path.normcase(os.path.abspath(v))==norm), None)
        if ek:
            self.current_file_path = file
            self.game_select_var.set(ek)
        else:
            key = f"[Browse] {os.path.basename(file)}"
            self.available_games[key] = file
            self.game_combo["values"] = list(self.available_games.keys())
            self.current_file_path = file
            self.game_select_var.set(key)
        self.update_file_info()

    def update_file_info(self):
        if not self.current_file_path or not os.path.isfile(self.current_file_path):
            self.lbl_info.config(text="[File khong ton tai]", fg="red"); return
        ext  = os.path.splitext(self.current_file_path)[1].lower()
        note = "\nYeu cau Java da cai + .jar mo duoc khi double-click" if ext == ".jar" else ""
        try: rel = os.path.relpath(self.current_file_path, self.base_dir)
        except Exception: rel = self.current_file_path
        self.lbl_info.config(text=f"OK: {rel}{note}", fg="green")

    # ==========================================================
    # LAYOUT
    # ==========================================================
    def on_window_resize(self, event):
        if self.resize_timer: self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(100, self.rearrange_layout)

    def rearrange_layout(self):
        instances = list(self.running_instances.values())
        if not instances:
            self.game_container.canvas.configure(scrollregion=(0, 0, 0, 0))
            return
        cw = self.game_area.winfo_width()
        if cw < 100: return
        try: iw = int(self.width_entry.get()) + 14
        except Exception: iw = 334
        cols = max(1, cw // iw)
        for i, d in enumerate(instances):
            d["wrapper"].grid(row=i//cols, column=i%cols, padx=(0,4), pady=(0,4), sticky="nw")
        self.game_container.scrollable_frame.update_idletasks()
        bbox = self.game_container.canvas.bbox("all")
        if bbox:
            self.game_container.canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))

    def increase_qty(self):
        try: v = int(self.qty_entry.get())
        except ValueError: v = 0
        self.qty_entry.delete(0, tk.END); self.qty_entry.insert(0, str(v+1))

    def decrease_qty(self):
        try: v = int(self.qty_entry.get())
        except ValueError: v = 2
        self.qty_entry.delete(0, tk.END); self.qty_entry.insert(0, str(max(1, v-1)))

    # ==========================================================
    # LAUNCH
    # ==========================================================
    def launch_direct_file(self, filepath):
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            logging.error(f"File khong ton tai: {filepath}")
            raise RuntimeError(f"File khong ton tai:\n{filepath}")
            
        logging.info(f"Yeu cau khoi chay: {filepath}")
        
        # Xử lý riêng cho game J2ME (.jar)
        if filepath.lower().endswith('.jar'):
            java_exe = os.path.join(self.base_dir, "jre", "bin", "java.exe")
            if not os.path.isfile(java_exe):
                java_exe = "java"
                
            microemu_jar = os.path.join(self.base_dir, "microemulator-2.0.4", "microemulator-2.0.4", "microemulator.jar")
            microemu_resizable = os.path.join(self.base_dir, "microemulator-2.0.4", "microemulator-2.0.4", "devices", "microemu-device-resizable.jar")
            
            if os.path.isfile(microemu_jar):
                logging.info(f"Phat hien game J2ME. Goi qua MicroEmulator: {microemu_jar}")
                
                # Cấu hình bỏ khung bàn phím, phóng to game Full màn hình theo size khung trắng
                if os.path.isfile(microemu_resizable):
                    cp_arg = f"{microemu_jar};{microemu_resizable}"
                    cmd = [
                        java_exe, "-cp", cp_arg, 
                        "org.microemu.app.Main", 
                        "--device", "org/microemu/device/resizable/device.xml", 
                        filepath
                    ]
                else:
                    cmd = [java_exe, "-cp", microemu_jar, "org.microemu.app.Main", filepath]
                    
                proc = subprocess.Popen(cmd, shell=False)
                logging.info(f"Da goi java.exe khoi chay MicroEmulator. PID (java): {proc.pid}")
                return WinProcWrapper(pid=proc.pid, hprocess=None)
            else:
                logging.warning("Khong tim thay microemulator.jar. Se chay jar truc tiep.")

        pid, hproc = shell_open_with_pid(filepath, os.path.dirname(filepath))
        logging.info(f"Da khoi chay chuong trinh thanh cong voi PID: {pid}")
        return WinProcWrapper(pid=pid, hprocess=hproc)

    def launch_one_game(self, filepath, w, h, title_hint):
        self.instance_counter += 1
        iid = self.instance_counter

        wrapper = ttk.LabelFrame(self.game_grid, text=f"G{iid}")
        wrapper.grid(row=999, column=999)

        ctrl = ttk.Frame(wrapper); ctrl.pack(fill=tk.X)
        sync = tk.BooleanVar(value=True)
        if iid != 1:
            ttk.Checkbutton(ctrl, variable=sync, text="Link").pack(side=tk.LEFT)
        else:
            tk.Label(ctrl, text="(Main)", fg="red", font=("Arial",9,"bold")).pack(side=tk.LEFT)
        lbl = tk.Label(ctrl, text="...", fg="orange"); lbl.pack(side=tk.RIGHT)

        cont = tk.Frame(wrapper, width=w, height=h, bg="black")
        cont.pack_propagate(False)
        cont.pack()

        try:
            proc = self.launch_direct_file(filepath)
            self.running_instances[iid] = {
                "process": proc, "wrapper": wrapper, "container": cont,
                "status_label": lbl, "sync_var": sync,
                "hwnd": None, "filepath": filepath,
                "win_w": w, "win_h": h,
            }
            self.rearrange_layout()
            self.update_close_range_ui()
            self.embed(iid, cont, proc, title_hint, w, h)
        except Exception as e:
            try: wrapper.destroy()
            except Exception: pass
            self.instance_counter -= 1
            messagebox.showerror("Loi khoi dong", str(e))

    # ==========================================================
    # FIND / EMBED
    # ==========================================================
    def find_window(self, pid, title_hint):
        pid_title = pid_only = title_only = None

        def cb(hwnd, _):
            nonlocal pid_title, pid_only, title_only
            if pid_title: return False
            try:
                if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd): return True
            except Exception: return True
            if hwnd in self.embedded_hwnds: return True
            try: txt = win32gui.GetWindowText(hwnd) or ""
            except Exception: txt = ""
            if "GDI+ Window" in txt or "MSCTFIME UI" in txt: return True
            try: style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            except Exception: style = 0
            if style & win32con.WS_CHILD: return True
            try: _, w_pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception: w_pid = 0
            title_ok = bool(title_hint and title_hint.lower() in txt.lower() and txt.strip())
            if pid and w_pid == pid:
                if title_ok: pid_title = hwnd; return False
                if pid_only is None: pid_only = hwnd
            elif title_ok and title_only is None:
                title_only = hwnd
            return True

        try: win32gui.EnumWindows(cb, None)
        except Exception: pass
        return pid_title or pid_only or title_only

    def embed(self, inst_id, container, proc, title_hint, w, h):
        def worker():
            data = self.running_instances.get(inst_id)
            if not data: return
            self.root.after(0, lambda: data["status_label"].config(text="Tim...", fg="blue"))
            hwnd = None
            logging.info(f"[G{inst_id}] Bat dau tim window... PID: {proc.pid if proc else 'N/A'}, TitleHint: {title_hint}")
            for i in range(600):
                if not self.running_instances.get(inst_id): return
                hwnd = self.find_window(proc.pid if proc else None, title_hint)
                if hwnd: 
                    logging.info(f"[G{inst_id}] Da tim thay HWND: {hwnd} (lan thu {i})")
                    break
                time.sleep(0.1)
            if not hwnd:
                logging.warning(f"[G{inst_id}] Timeout 60s! Khong tim thay window nao khop voi PID hoac Title: {title_hint}")
            self.root.after(0, lambda: self.finalize(inst_id, hwnd, container, w, h))
        threading.Thread(target=worker, daemon=True).start()

    def finalize(self, inst_id, hwnd, container, w, h):
        data = self.running_instances.get(inst_id)
        if not data: return
        if not hwnd:
            data["status_label"].config(text="Khong thay window!", fg="red"); return
        try:
            logging.info(f"[G{inst_id}] Tien hanh Embed (nhung) Window HWND: {hwnd}")
            container.config(width=w, height=h)
            container.pack_propagate(False)
            self.root.update_idletasks()

            self.embedded_hwnds.append(hwnd)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style = (style & ~(
                win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_THICKFRAME
                | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX
                | win32con.WS_SYSMENU | win32con.WS_BORDER
            )) | win32con.WS_CHILD | win32con.WS_VISIBLE
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex = ex & ~(0x00040000 | win32con.WS_EX_TOOLWINDOW)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)

            win32gui.SetParent(hwnd, container.winfo_id())
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, w, h, 0x0004|0x0020|0x0040)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(hwnd)

            data["hwnd"] = hwnd
            data["status_label"].config(
                text="MASTER" if inst_id == 1 else "OK",
                fg="red"   if inst_id == 1 else "green"
            )
        except Exception as e:
            print("Finalize error:", e)
            data["status_label"].config(text=f"Loi nhung: {e}", fg="red")

    # ==========================================================
    # START / STOP INSTANCES
    # ==========================================================
    def start_game_instances(self):
        if not self.current_file_path:
            messagebox.showwarning("Loi", f"Khong co file.\nBo file vao:\n{self.game_dir}"); return
        self.current_file_path = os.path.abspath(self.current_file_path)
        if not os.path.isfile(self.current_file_path):
            messagebox.showerror("Loi", f"File khong ton tai:\n{self.current_file_path}"); return
        title_hint = self.title_entry.get().strip()
        if not title_hint:
            messagebox.showwarning("Thieu ten cua so", "Ban phai nhap ten cua so."); return
        try: qty = max(1, int(self.qty_entry.get()))
        except ValueError: messagebox.showwarning("Loi", "So luong phai la so nguyen."); return
        try: w, h = int(self.width_entry.get()), int(self.height_entry.get())
        except ValueError: messagebox.showwarning("Loi", "Kich thuoc phai la so nguyen."); return

        fp = self.current_file_path
        def run():
            for i in range(qty):
                # 1. Yêu cầu giao diện mở game
                self.root.after(0, lambda f=fp: self.launch_one_game(f, w, h, title_hint))
                
                # 2. Đợi 6 giây cho Game load xong cửa sổ Java
                time.sleep(6.0)
                
                # 3. Lấy thông tin tài khoản theo thứ tự
                acc = self.accounts[i] if i < len(self.accounts) else None
                
                # 4. Chạy quá trình Auto Login cho game vừa mở (Sẽ đợi chạy xong login mới mở tab mới)
                if acc:
                    iid = self.instance_counter
                    self.auto_login_task(iid, acc)
                
                # 5. Đợi thêm 1 chút xíu trước khi mở game tiếp theo
                time.sleep(1.0)
        threading.Thread(target=run, daemon=True).start()

    def close_one_instance(self, iid):
        data = self.running_instances.get(iid)
        if not data: return
        hwnd = data.get("hwnd"); proc = data.get("process")
        try:
            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception: pass
        time.sleep(0.7)
        try:
            if proc and proc.pid:
                subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                if proc: proc.terminate()
            except Exception: pass
        try: data["wrapper"].destroy()
        except Exception: pass
        if hwnd in self.embedded_hwnds:
            try: self.embedded_hwnds.remove(hwnd)
            except ValueError: pass
        try:
            if proc: proc.close_handle()
        except Exception: pass
        if iid in self.running_instances:
            del self.running_instances[iid]
        self.update_close_range_ui()

    def stop_all_instances(self):
        for iid in list(self.running_instances.keys()):
            self.close_one_instance(iid)
        self.running_instances.clear()
        self.embedded_hwnds.clear()
        self.instance_counter = 0
        self.update_close_range_ui()

    def on_closing(self):
        if messagebox.askokcancel("Thoat", "Dong tool va tat het game?"):
            self._auto_click_stop_event.set()
            if hasattr(self, 'quick_panel'):
                self.quick_panel.destroy_all()
            self.broadcaster.stop()
            self.stop_all_instances()
            self.root.destroy()
            os._exit(0)

    # ==========================================================
    # MIRROR / SYNC
    # ==========================================================
    def toggle_modes(self):
        self.is_master_mouse_running  = self.master_mouse_var.get()
        self.is_master_rmouse_running = self.master_rmouse_var.get()
        self.is_master_scroll_running = self.master_scroll_var.get()
        self.is_master_key_running    = self.master_key_var.get()

    def start_input_listeners(self):

        def _in_master(self, x, y):
            bounds = self._master_bounds
            if not bounds:
                try:
                    master = self.running_instances.get(1)
                    if master and master.get("container"):
                        c = master["container"]
                        rx = c.winfo_rootx(); ry = c.winfo_rooty()
                        rw = c.winfo_width(); rh = c.winfo_height()
                        if rx <= x <= rx + rw and ry <= y <= ry + rh:
                            return x - rx, y - ry
                except Exception:
                    pass
                return None
            rx, ry, rw, rh = bounds
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return x - rx, y - ry
            return None

        def _get_active_context():
            """Kiểm tra xem bạn đang click chuột vào Game nào"""
            active_hwnd = win32gui.GetForegroundWindow()
            tool_hwnd = self.root.winfo_id()
            tool_parent = ctypes.windll.user32.GetParent(tool_hwnd)
            
            if active_hwnd == tool_hwnd or active_hwnd == tool_parent:
                return "tool"
                
            for iid, d in list(self.running_instances.items()):
                if d.get("hwnd") == active_hwnd:
                    return iid
            return None

        def on_click(x, y, button, pressed):
            if pressed: return
            is_left  = (button == Button.left)
            is_right = (button == Button.right)
            if not (is_left and self.is_master_mouse_running) and \
               not (is_right and self.is_master_rmouse_running):
                return
            now = time.time()
            if is_left:
                if now - self.last_lclick_time < 0.03: return
                self.last_lclick_time = now
            else:
                if now - self.last_rclick_time < 0.03: return
                self.last_rclick_time = now
            rel = _in_master(self, x, y)
            if rel:
                btn_type = "right" if is_right else "left"
                self.broadcaster.submit(self._do_broadcast_mouse, rel[0], rel[1], btn_type)

        def on_scroll(x, y, dx, dy):
            if not self.is_master_scroll_running: return
            rel = _in_master(self, x, y)
            if rel:
                self.broadcaster.submit(self._do_broadcast_scroll, rel[0], rel[1], dy)

        def on_key(k, down):
            ctx = _get_active_context()
            if ctx is None: return  # Nếu đang lướt Chrome/Zalo bên ngoài thì phớt lờ

            vk = self.get_vk(k)
            if not vk: return

            if ctx == 1:
                # CHỈ G1 Master mới có quyền điều khiển đồng bộ phím cho các taq khác
                # Luôn gửi phím cho chính G1 trước
                self.broadcaster.submit(self._do_send_single_key, 1, vk, down, k)
                # Nếu bật Link Phim -> broadcast sang các taq còn lại
                if self.is_master_key_running:
                    self.broadcaster.submit(self._do_broadcast_key, vk, down, k)
            elif ctx not in ("tool", None):
                # G2, G3... -> Ép gửi phím vào đúng tab đó để chơi tay độc lập
                self.broadcaster.submit(self._do_send_single_key, ctx, vk, down, k)
            # ctx == "tool": đang gõ vào UI của tool → bỏ qua

        self.mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
        self.mouse_listener.start()
        self.key_listener = keyboard.Listener(
            on_press=lambda k:  on_key(k, True),
            on_release=lambda k: on_key(k, False)
        )
        self.key_listener.start()

    def _get_taq_delay(self):
        try: return self.sync_delay_var.get() / 1000.0
        except Exception: return 0.0

    def _do_broadcast_mouse(self, x, y, btn_type="left"):
        mode  = self.click_mode
        delay = self._get_taq_delay()

        # ==========================================
        # 1. LƯU LẠI TỌA ĐỘ VÀ CỬA SỔ HIỆN TẠI
        # ==========================================
        orig_x, orig_y = win32api.GetCursorPos()
        current_hwnd = win32gui.GetForegroundWindow()

        # ==========================================
        # 2. NÉM CHUỘT ĐI CLICK CÁC TAB CON
        # ==========================================
        for iid, d in list(self.running_instances.items()):
            if iid == 1 or not d["sync_var"].get(): continue
            hwnd = d.get("hwnd")
            container = d.get("container")
            if not hwnd: continue
            
            try:
                if mode == "direct" and container and DIRECTINPUT_AVAILABLE:
                    win32gui.SetForegroundWindow(self.root.winfo_id())
                    abs_x = container.winfo_rootx() + x
                    abs_y = container.winfo_rooty() + y
                    pydirectinput.moveTo(abs_x, abs_y)
                    if btn_type == "left":
                        pydirectinput.click()
                    else:
                        pydirectinput.rightClick()
                else:
                    # mode == "input"
                    send_click_sendinput(hwnd, x, y, btn_type)
            except Exception as e:
                print(f"[ERR] G{iid}: {e}")
                
            if delay > 0:
                time.sleep(delay)

        # ==========================================
        # 3. TRẢ CHUỘT & TRẢ FOCUS VỀ LẠI CHỖ CŨ
        # ==========================================
        try:
            # Kéo con trỏ chuột vật lý về lại đúng điểm ban đầu
            win32api.SetCursorPos((orig_x, orig_y))
            
            # Trả lại quyền Focus cho cửa sổ bạn đang dùng (để không bị mất dấu gõ phím)
            if current_hwnd:
                win32gui.SetForegroundWindow(current_hwnd)
        except Exception:
            pass

    def _do_broadcast_scroll(self, x, y, dy):
        delta = int(dy * 120)
        lp    = win32api.MAKELONG(x, y)
        for iid, d in list(self.running_instances.items()):
            if iid == 1 or not d["sync_var"].get(): continue
            hwnd = d.get("hwnd")
            if not hwnd: continue
            try:
                win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL,
                                     win32api.MAKELONG(0, delta), lp)
            except Exception as e:
                print(f"[Scroll] {e}")

    def _do_broadcast_key(self, vk, down, key_obj):
        scan = win32api.MapVirtualKey(vk, 0)
        lp   = (scan << 16) | 1
        if key_obj in [Key.up, Key.down, Key.left, Key.right]:
            lp |= (1 << 24)
        msg = win32con.WM_KEYDOWN if down else win32con.WM_KEYUP
        if not down:
            lp |= (1 << 30) | (1 << 31)
        delay = self._get_taq_delay()
        for iid, d in list(self.running_instances.items()):
            if iid == 1 or not d["sync_var"].get(): continue
            hwnd = d.get("hwnd")
            if hwnd:
                try: win32api.PostMessage(hwnd, msg, vk, lp)
                except Exception: pass
            if delay > 0:
                time.sleep(delay)

    def get_vk(self, key):
        if hasattr(key, "vk"): return key.vk
        specials = {
            Key.up: 0x26, Key.down: 0x28, Key.left: 0x25, Key.right: 0x27,
            Key.space: 0x20, Key.enter: 0x0D, Key.esc: 0x1B,
        }
        if key in specials: return specials[key]
        if hasattr(key, "char") and key.char: return ord(key.char.upper())
        return None
    def _do_send_single_key(self, iid, vk, down, key_obj):
        """Gửi phím vào 1 tab cụ thể để chơi tay độc lập"""
        scan = win32api.MapVirtualKey(vk, 0)
        lp   = (scan << 16) | 1
        if key_obj in [Key.up, Key.down, Key.left, Key.right]:
            lp |= (1 << 24)
        msg = win32con.WM_KEYDOWN if down else win32con.WM_KEYUP
        if not down:
            lp |= (1 << 30) | (1 << 31)
        d    = self.running_instances.get(iid)
        hwnd = d.get("hwnd") if d else None
        if hwnd:
            try: win32api.PostMessage(hwnd, msg, vk, lp)
            except Exception: pass

    # ==========================================================
    # ACCOUNT DASHBOARD & AUTO LOGIN
    # ==========================================================
    def load_accounts(self):
        self.accounts = []
        try:
            if os.path.isfile("accounts.json"):
                with open("accounts.json", "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
        except Exception as e:
            print(f"Loi doc accounts.json: {e}")

    def save_accounts(self):
        try:
            with open("accounts.json", "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Loi luu accounts.json: {e}")

    def open_account_manager(self):
        self.load_accounts()
        top = tk.Toplevel(self.root)
        top.title("Quan Ly Tai Khoan")
        top.geometry("600x400")
        top.transient(self.root)
        top.configure(bg="#222222") # Dark mode
        
        lbl_hint = tk.Label(top, text="Click đúp vào dòng để Bật/Tắt Checkbox [ x ]", bg="#222222", fg="#00FF00", font=("Arial", 11, "bold"))
        lbl_hint.pack(pady=5)
        
        # Style cho Treeview
        style = ttk.Style(top)
        style.theme_use("clam")
        style.configure("Treeview", 
                        background="#333333", 
                        foreground="white", 
                        fieldbackground="#333333", 
                        rowheight=30, 
                        font=("Arial", 10))
        style.configure("Treeview.Heading", background="#444444", foreground="white", font=("Arial", 10, "bold"))
        style.map("Treeview", background=[("selected", "#0055AA")])
        
        columns = ("check", "username", "password", "server")
        tree = ttk.Treeview(top, columns=columns, show="headings", style="Treeview")
        tree.heading("check", text="Chon")
        tree.column("check", width=50, anchor=tk.CENTER)
        tree.heading("username", text="Tai Khoan")
        tree.heading("password", text="Mat Khau")
        tree.heading("server", text="Server")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Insert data with initial checkbox [ x ]
        for acc in self.accounts:
            tree.insert("", tk.END, values=("[ x ]", acc.get("username", ""), "******", acc.get("server", "")), tags=(str(acc.get("server_clicks", 2)),))
            
        def toggle_check(event):
            item = tree.identify_row(event.y)
            if item:
                vals = list(tree.item(item, "values"))
                if vals[0] == "[ x ]":
                    vals[0] = "[   ]"
                else:
                    vals[0] = "[ x ]"
                tree.item(item, values=vals)
                
        tree.bind("<Double-1>", toggle_check)
            
        btn_frame = tk.Frame(top, bg="#222222")
        btn_frame.pack(fill=tk.X, padx=10, pady=(5,10))
        
        def _login_all():
            selected_accs = []
            for child in tree.get_children():
                vals = tree.item(child, "values")
                tags = tree.item(child, "tags")
                clicks = int(tags[0]) if tags else 2
                if vals[0] == "[ x ]":
                    selected_accs.append({
                        "username": vals[1],
                        "password": self.get_real_password(vals[1]),
                        "server": vals[3],
                        "server_clicks": clicks
                    })
            top.destroy()
            self.auto_login_all(selected_accs)
            
        btn_login = tk.Button(btn_frame, text="LOGIN HANG LOAT (Chỉ tab được tick)", bg="#008CBA", fg="white", font=("Arial", 10, "bold"), command=_login_all)
        btn_login.pack(side=tk.LEFT, ipadx=10, ipady=5)
        btn_close = tk.Button(btn_frame, text="Dong", bg="#555555", fg="white", font=("Arial", 10), command=top.destroy)
        btn_close.pack(side=tk.RIGHT, ipadx=10, ipady=5)

    def get_real_password(self, username):
        for acc in self.accounts:
            if acc.get("username") == username:
                return acc.get("password")
        return ""

    def auto_login_all(self, selected_accs):
        if not selected_accs:
            messagebox.showwarning("Thong bao", "Ban chua tick chon tai khoan nao!")
            return
            
        if not self.current_file_path or not os.path.isfile(self.current_file_path):
            messagebox.showwarning("Loi", "Ban phai chon file game o panel chinh truoc.")
            return

        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, str(len(selected_accs)))
        
        fp = self.current_file_path
        w = int(self.width_entry.get())
        h = int(self.height_entry.get())
        title_hint = self.title_entry.get().strip()
        
        def run_all_macro():
            for idx, acc in enumerate(selected_accs):
                self.root.after(0, lambda f=fp: self.launch_one_game(f, w, h, title_hint))
                time.sleep(6.0) 
                iid = self.instance_counter
                self.auto_login_task(iid, acc)
                time.sleep(2.0)
                
        threading.Thread(target=run_all_macro, daemon=True).start()

    hardware_input_lock = threading.Lock()

    def auto_login_task(self, iid, acc):
        d = self.running_instances.get(iid)
        if not d: return
        hwnd = d.get("hwnd")
        if not hwnd: return
        
        x_tk, y_tk = 160, 140
        x_mk, y_mk = 160, 215
        x_sv, y_sv = 160, 305
        
        def hw_click(x, y):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
            except: pass
            send_click_sendinput(hwnd, x, y, "left")

        def hw_type(text):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
            except: pass
            for c in text:
                self.keyboard_controller.press(c)
                time.sleep(0.01)
                self.keyboard_controller.release(c)
                time.sleep(0.05)

        def hw_vk(vk_code, presses=1):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
            except: pass
            
            key = None
            if vk_code == 0x0D: key = Key.enter
            elif vk_code == 0x08: key = Key.backspace
            elif vk_code == 0x28: key = Key.down
            elif vk_code == 0x26: key = Key.up
            elif vk_code == 0x71: key = Key.f2  # F2 = Right Softkey
            elif vk_code == 0x70: key = Key.f1  # F1 = Left Softkey
            
            if not key: return
            
            for _ in range(presses):
                self.keyboard_controller.press(key)
                time.sleep(0.01)
                self.keyboard_controller.release(key)
                time.sleep(0.1)

        w = d.get("win_w", 320)
        h = d.get("win_h", 450)
        
        # Tọa độ tương đối dựa trên tâm màn hình (chuẩn xác cho mọi độ phân giải của game Teamobi)
        center_x = w // 2
        center_y = h // 2
        
        x_tk, y_tk = center_x, center_y - 85
        x_mk, y_mk = center_x, center_y - 10
        x_sv, y_sv = center_x, center_y + 80
        x_login, y_login = center_x, center_y + 115  # Nằm ngay dưới ô Server, tránh chạm vào nút Resize
        
        # --- BƯỚC 1: Chọn MIDlet "Hai tac" và bấm Start ---
        logging.info(f"Auto-Login [G{iid}]: Bam Start game...")
        # 1. Click vào danh sách ở trên cùng để Focus (Y=50 là chắc chắn trúng list game)
        hw_click(center_x, 50)
        time.sleep(0.3)
        
        # 2. Gửi phím Enter để Start game luôn (Không click chuột xuống dưới vì sẽ dính nút Resize)
        hw_vk(0x0D, 1)
        time.sleep(0.5)
        # Gửi thêm phím F2 dự phòng nếu Enter không ăn
        hw_vk(0x71, 1)
        
        # Đợi game tải (khoảng 8 giây cho game J2ME tải dữ liệu)
        logging.info(f"Auto-Login [G{iid}]: Cho 8 giay de game tai xong...")
        for i in range(8):
            time.sleep(1)
        logging.info(f"Auto-Login [G{iid}]: Bat dau nhap tai khoan mat khau...")
            
        with hardware_input_lock:
            # Click vao Tai Khoan
            hw_click(x_tk, y_tk)
            time.sleep(0.5)
        
            # Xóa tài khoản cũ (bấm backspace 20 lần)
            logging.info(f"Auto-Login [G{iid}]: Xoa tai khoan cu...")
            hw_vk(0x08, 20)
            
            # Nhap Tai Khoan
            logging.info(f"Auto-Login [G{iid}]: Nhap tai khoan: {acc.get('username')}")
            hw_type(acc.get("username", ""))
            time.sleep(0.5)
            
            # Bam OK (Enter) -> Trong game nay nhập xong thường bấm Enter để xuống
            hw_vk(0x0D, 1)
            time.sleep(0.5)
            
            # Click vao Mat Khau
            hw_click(x_mk, y_mk)
            time.sleep(0.5)
            
            # Xoa Mat Khau cu
            hw_vk(0x08, 20)
            
            # Nhap Mat Khau
            hw_type(acc.get("password", ""))
            time.sleep(0.5)
            
            # Bam OK (Enter)
            hw_vk(0x0D, 1)
            time.sleep(0.5)
            
            # Click vao Server
            hw_click(x_sv, y_sv)
            time.sleep(0.5)
            
            # Bam phim Xuong (Arrow Down)
            clicks = acc.get("server_clicks", 2)
            # Bấm Lên 5 lần để reset về Server đầu tiên cho chắc ăn
            hw_vk(0x26, 5)
            # Bấm Xuống theo cấu hình
            hw_vk(0x28, clicks)
            time.sleep(0.5)
            
            # Bam Enter de chon Server
            hw_vk(0x0D, 1)
            time.sleep(0.5)
            
            # Click vao giua man hinh de vao game
            hw_click(x_login, y_login)
            logging.info(f"Auto-Login [G{iid}]: Hoan tat quy trinh!")

if __name__ == "__main__":
    root = tk.Tk()
    app  = TapGameManager(root)
    root.mainloop()