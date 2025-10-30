#!/usr/bin/env python3
"""
Clipboard Manager for Linux Mint (Windows 11 Style) - FIXED
"""

import pyperclip as pc
from collections import deque
import time
import threading
import tkinter as tk
from tkinter import font
from pynput import keyboard as pynput_kb, mouse as pynput_mouse
from pynput.keyboard import Controller, Key
import json
import os
import sys

CONFIG_FILE = os.path.expanduser("~/.clipboard_manager_config.json")

class ClipboardManager:

    def __init__(self):
        self.max_size = 100
        self.auto_paste = True
        self.clip_history = deque(maxlen=self.max_size)
        self.last_saved = ""
        self.running = True
        self.keyboard_controller = Controller()
        self.ui_window = None
        self.is_ui_open = False
        self.pinned = False

        self.needs_show_ui = False
        self.needs_paste_latest = False

        self.root = tk.Tk()
        self.root.withdraw()

        self.load_config()
        self.monitor_thread = threading.Thread(target=self.watch_clipboard, daemon=True)
        self.monitor_thread.start()

        # Hotkeys
        def _request_show_ui():
            self.needs_show_ui = True

        def _request_paste_latest():
            self.needs_paste_latest = True

        try:
            self.hotkey_listener = pynput_kb.GlobalHotKeys({
                '<ctrl>+<alt>+v': _request_show_ui,
                '<ctrl>+<shift>+v': _request_paste_latest,
            })
            self.hotkey_listener.start()
            print("🚀 Clipboard Manager Started (Linux Edition)")
            print("   Press Ctrl+Alt+V to toggle history")
            print("   Click outside or press Esc to close")
        except Exception as e:
            print(f"⚠️ Hotkey error: {e}")

        # Global mouse listener for auto-hide
        self.mouse_listener = pynput_mouse.Listener(on_click=self._on_global_click)
        self.mouse_listener.start()

    def _on_global_click(self, x, y, button, pressed):
        if pressed and self.is_ui_open and not self.pinned and self.ui_window:
            try:
                x0 = self.ui_window.winfo_x()
                y0 = self.ui_window.winfo_y()
                x1 = x0 + self.ui_window.winfo_width()
                y1 = y0 + self.ui_window.winfo_height()
                if not (x0 <= x <= x1 and y0 <= y <= y1):
                    self.root.after(0, self.close_ui)
            except:
                pass

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.max_size = config.get('max_size', 100)
                    self.auto_paste = config.get('auto_paste', True)
                    self.clip_history = deque(config.get('history', []), maxlen=self.max_size)
        except Exception as e:
            print(f"⚠️ Config load error: {e}")

    def save_config(self):
        try:
            config = {
                'max_size': self.max_size,
                'auto_paste': self.auto_paste,
                'history': list(self.clip_history)
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️ Config save error: {e}")

    def watch_clipboard(self):
        try:
            self.last_saved = pc.paste()
        except:
            self.last_saved = ""

        while self.running:
            try:
                current = pc.paste()
                if current and current != self.last_saved:
                    if current not in self.clip_history:
                        self.clip_history.append(current)
                        self.save_config()
                    self.last_saved = current
            except Exception:
                pass
            time.sleep(0.3)

    def paste_text(self, text):
        pc.copy(text)
        time.sleep(0.05)
        try:
            self.keyboard_controller.press(Key.ctrl_l)
            time.sleep(0.02)
            self.keyboard_controller.press('v')
            self.keyboard_controller.release('v')
            self.keyboard_controller.release(Key.ctrl_l)
        except Exception:
            pass

    def paste_latest(self):
        if self.clip_history:
            latest = list(self.clip_history)[-1]
            self.paste_text(latest)

    def toggle_ui(self):
        if self.is_ui_open:
            self.close_ui()
        else:
            self.show_ui()

    def close_ui(self):
        if self.ui_window:
            try:
                self.ui_window.destroy()
            except:
                pass
            self.ui_window = None
            self.is_ui_open = False
            self.pinned = False

    def show_ui(self):
        if self.is_ui_open:
            return

        self.is_ui_open = True
        self.ui_window = tk.Toplevel()
        self.ui_window.title("Clipboard")
        self.ui_window.overrideredirect(True)
        self.ui_window.attributes('-topmost', True)

        bg_color = "#ffffff"
        hover_color = "#f3f3f3"
        select_color = "#8fa876"
        border_color = "#e0e0e0"
        text_color = "#1f1f1f"
        secondary_text = "#707070"

        width = 400
        max_height = 500

        # Position near mouse
        try:
            from pynput.mouse import Controller as MouseController
            mouse = MouseController()
            mx, my = mouse.position
            screen_width = self.ui_window.winfo_screenwidth()
            screen_height = self.ui_window.winfo_screenheight()
            x = min(max(mx - width // 2, 0), screen_width - width)
            y = min(max(my + 20, 0), screen_height - max_height)
        except:
            x, y = 100, 100

        main_frame = tk.Frame(self.ui_window, bg=bg_color,
                             highlightbackground=border_color,
                             highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Draggable header
        header = tk.Frame(main_frame, bg=bg_color, height=40, cursor="fleur")
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        header.pack_propagate(False)

        self._drag_data = {"x": 0, "y": 0}
        def start_drag(event):
            self._drag_data["x"] = event.x_root - self.ui_window.winfo_x()
            self._drag_data["y"] = event.y_root - self.ui_window.winfo_y()

        def do_drag(event):
            x = event.x_root - self._drag_data["x"]
            y = event.y_root - self._drag_data["y"]
            self.ui_window.geometry(f"+{x}+{y}")

        header.bind("<Button-1>", start_drag)
        header.bind("<B1-Motion>", do_drag)

        title_font = font.Font(family="Ubuntu", size=11, weight="bold")
        title_label = tk.Label(header, text="📋 Clipboard",
                              font=title_font, bg=bg_color, fg=text_color)
        title_label.pack(side=tk.LEFT, pady=5)

        pin_btn = tk.Label(header, text="📌", font=("Ubuntu", 14),
                          bg=bg_color, fg=secondary_text, cursor="hand2")
        pin_btn.pack(side=tk.RIGHT, padx=5)

        def toggle_pin(e):
            self.pinned = not self.pinned
            pin_btn.config(text="📍" if self.pinned else "📌")

        pin_btn.bind("<Button-1>", toggle_pin)

        # Search
        search_frame = tk.Frame(main_frame, bg=bg_color)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=("Ubuntu", 10), relief=tk.FLAT,
                               bg="#f5f5f5", fg=secondary_text)
        search_entry.pack(fill=tk.X, ipady=6, padx=2, pady=2)
        search_entry.insert(0, "🔍 Search clipboard...")

        def on_focus_in(e):
            if search_entry.get() == "🔍 Search clipboard...":
                search_entry.delete(0, tk.END)
                search_entry.config(fg=text_color)

        def on_focus_out(e):
            if not search_entry.get():
                search_entry.insert(0, "🔍 Search clipboard...")
                search_entry.config(fg=secondary_text)

        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)

        separator = tk.Frame(main_frame, bg=border_color, height=1)
        separator.pack(fill=tk.X, padx=10)

        # Scrollable area
        canvas_frame = tk.Frame(main_frame, bg=bg_color)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, bg=bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=bg_color)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        item_frames = []
        selected_index = [0]

        def select_item(idx):
            for i, frame in enumerate(item_frames):
                is_selected = (i == idx)
                color = select_color if is_selected else bg_color
                fg = "white" if is_selected else text_color
                frame.config(bg=color)
                for child in frame.winfo_children():
                    child.config(bg=color)
                    if isinstance(child, tk.Label):
                        child.config(fg=fg)
                    for grand in child.winfo_children():
                        grand.config(bg=color)
                        if isinstance(grand, tk.Label):
                            grand.config(fg=fg)
            selected_index[0] = idx

        def paste_item(idx):
            if 0 <= idx < len(self.clip_history):
                actual_idx = len(self.clip_history) - 1 - idx
                text = list(self.clip_history)[actual_idx]
                self.close_ui()
                time.sleep(0.05)
                if self.auto_paste:
                    self.paste_text(text)
                else:
                    pc.copy(text)

        # Populate items
        if not self.clip_history:
            tk.Label(scrollable_frame, text="No clipboard history yet", bg=bg_color, fg=secondary_text).pack(pady=50)
        else:
            for i, item in enumerate(reversed(list(self.clip_history))):
                item_frame = tk.Frame(scrollable_frame, bg=bg_color, cursor="hand2")
                item_frame.pack(fill=tk.X, pady=2)
                item_frames.append(item_frame)

                inner = tk.Frame(item_frame, bg=bg_color)
                inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

                preview = item.replace('\n', ' ').strip()
                if len(preview) > 80:
                    preview = preview[:80] + '...'

                text_label = tk.Label(inner, text=preview, font=("Ubuntu", 10),
                                     bg=bg_color, fg=text_color, anchor="w")
                text_label.pack(fill=tk.X)

                # Type
                if item.startswith(('http://', 'https://')):
                    typ = "🔗 Link"
                elif item.replace('.','').replace('-','').isdigit():
                    typ = "🔢 Number"
                elif '\n' in item:
                    typ = f"📄 {len(item.split())} words"
                else:
                    typ = "Text"

                type_label = tk.Label(inner, text=typ, font=("Ubuntu", 8),
                                     bg=bg_color, fg=secondary_text, anchor="w")
                type_label.pack(fill=tk.X)

                # Click handler
                def make_click_handler(idx):
                    return lambda e: paste_item(idx)

                item_frame.bind("<Button-1>", make_click_handler(i))
                inner.bind("<Button-1>", make_click_handler(i))
                text_label.bind("<Button-1>", make_click_handler(i))
                type_label.bind("<Button-1>", make_click_handler(i))

                # Hover
                def make_enter_handler(idx):
                    return lambda e: (
                        item_frame.config(bg=hover_color),
                        inner.config(bg=hover_color),
                        text_label.config(bg=hover_color),
                        type_label.config(bg=hover_color)
                    ) if selected_index[0] != idx else None

                def make_leave_handler(idx):
                    return lambda e: (
                        item_frame.config(bg=bg_color),
                        inner.config(bg=bg_color),
                        text_label.config(bg=bg_color),
                        type_label.config(bg=bg_color)
                    ) if selected_index[0] != idx else None

                item_frame.bind("<Enter>", make_enter_handler(i))
                item_frame.bind("<Leave>", make_leave_handler(i))

        # Keyboard handling — bound ONLY to ui_window
        def on_key(event):
            if not item_frames:
                return
            if event.keysym == "Down":
                select_item(min(selected_index[0] + 1, len(item_frames) - 1))
            elif event.keysym == "Up":
                select_item(max(selected_index[0] - 1, 0))
            elif event.keysym == "Return":
                paste_item(selected_index[0])
            elif event.keysym == "Escape":
                if not self.pinned:
                    self.close_ui()
            elif event.keysym == "Delete":
                if 0 <= selected_index[0] < len(self.clip_history):
                    actual_idx = len(self.clip_history) - 1 - selected_index[0]
                    text_to_remove = list(self.clip_history)[actual_idx]
                    self.clip_history.remove(text_to_remove)
                    self.save_config()
                    self.close_ui()
                    self.show_ui()

        self.ui_window.bind("<Key>", on_key)
        self.ui_window.focus_set()
        self.ui_window.grab_set()  # Modal-like behavior

        # Search
        def on_search_change(*_):
            query = search_var.get().lower()
            if query in ("", "🔍 search clipboard..."):
                for f in item_frames:
                    f.pack(fill=tk.X, pady=2)
                return
            for i, (frame, item) in enumerate(zip(item_frames, reversed(list(self.clip_history)))):
                frame.pack(fill=tk.X, pady=2) if query in item.lower() else frame.pack_forget()

        search_var.trace("w", on_search_change)

        # Footer
        footer = tk.Frame(main_frame, bg=bg_color, height=30)
        footer.pack(fill=tk.X, padx=10, pady=(5, 10))
        info = f"{len(self.clip_history)} items • ↑↓ Enter Del"
        tk.Label(footer, text=info, font=("Ubuntu", 8), bg=bg_color, fg=secondary_text).pack()

        # Finalize
        items_height = min(len(item_frames) * 70, 400)
        total_height = min(items_height + 150, max_height)
        self.ui_window.geometry(f"{width}x{total_height}+{x}+{y}")

        if item_frames:
            select_item(0)

    def stop(self):
        self.running = False
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        self.save_config()


if __name__ == "__main__":
    try:
        manager = ClipboardManager()
        while True:
            try:
                manager.root.update()
            except tk.TclError:
                break

            if manager.needs_show_ui:
                manager.needs_show_ui = False
                manager.toggle_ui()

            if manager.needs_paste_latest:
                manager.needs_paste_latest = False
                manager.paste_latest()

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n👋 Stopped")
        manager.stop()
        sys.exit(0)#!/usr/bin/env python3
"""
Clipboard Manager for Linux Mint (Windows 11 Style) - FIXED
"""

import pyperclip as pc
from collections import deque
import time
import threading
import tkinter as tk
from tkinter import font
from pynput import keyboard as pynput_kb, mouse as pynput_mouse
from pynput.keyboard import Controller, Key
import json
import os
import sys

CONFIG_FILE = os.path.expanduser("~/.clipboard_manager_config.json")

class ClipboardManager:

    def __init__(self):
        self.max_size = 100
        self.auto_paste = True
        self.clip_history = deque(maxlen=self.max_size)
        self.last_saved = ""
        self.running = True
        self.keyboard_controller = Controller()
        self.ui_window = None
        self.is_ui_open = False
        self.pinned = False

        self.needs_show_ui = False
        self.needs_paste_latest = False

        self.root = tk.Tk()
        self.root.withdraw()

        self.load_config()
        self.monitor_thread = threading.Thread(target=self.watch_clipboard, daemon=True)
        self.monitor_thread.start()

        # Hotkeys
        def _request_show_ui():
            self.needs_show_ui = True

        def _request_paste_latest():
            self.needs_paste_latest = True

        try:
            self.hotkey_listener = pynput_kb.GlobalHotKeys({
                '<ctrl>+<alt>+v': _request_show_ui,
                '<ctrl>+<shift>+v': _request_paste_latest,
            })
            self.hotkey_listener.start()
            print("🚀 Clipboard Manager Started (Linux Edition)")
            print("   Press Ctrl+Alt+V to toggle history")
            print("   Click outside or press Esc to close")
        except Exception as e:
            print(f"⚠️ Hotkey error: {e}")

        # Global mouse listener for auto-hide
        self.mouse_listener = pynput_mouse.Listener(on_click=self._on_global_click)
        self.mouse_listener.start()

    def _on_global_click(self, x, y, button, pressed):
        if pressed and self.is_ui_open and not self.pinned and self.ui_window:
            try:
                x0 = self.ui_window.winfo_x()
                y0 = self.ui_window.winfo_y()
                x1 = x0 + self.ui_window.winfo_width()
                y1 = y0 + self.ui_window.winfo_height()
                if not (x0 <= x <= x1 and y0 <= y <= y1):
                    self.root.after(0, self.close_ui)
            except:
                pass

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.max_size = config.get('max_size', 100)
                    self.auto_paste = config.get('auto_paste', True)
                    self.clip_history = deque(config.get('history', []), maxlen=self.max_size)
        except Exception as e:
            print(f"⚠️ Config load error: {e}")

    def save_config(self):
        try:
            config = {
                'max_size': self.max_size,
                'auto_paste': self.auto_paste,
                'history': list(self.clip_history)
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️ Config save error: {e}")

    def watch_clipboard(self):
        try:
            self.last_saved = pc.paste()
        except:
            self.last_saved = ""

        while self.running:
            try:
                current = pc.paste()
                if current and current != self.last_saved:
                    if current not in self.clip_history:
                        self.clip_history.append(current)
                        self.save_config()
                    self.last_saved = current
            except Exception:
                pass
            time.sleep(0.3)

    def paste_text(self, text):
        pc.copy(text)
        time.sleep(0.05)
        try:
            self.keyboard_controller.press(Key.ctrl_l)
            time.sleep(0.02)
            self.keyboard_controller.press('v')
            self.keyboard_controller.release('v')
            self.keyboard_controller.release(Key.ctrl_l)
        except Exception:
            pass

    def paste_latest(self):
        if self.clip_history:
            latest = list(self.clip_history)[-1]
            self.paste_text(latest)

    def toggle_ui(self):
        if self.is_ui_open:
            self.close_ui()
        else:
            self.show_ui()

    def close_ui(self):
        if self.ui_window:
            try:
                self.ui_window.destroy()
            except:
                pass
            self.ui_window = None
            self.is_ui_open = False
            self.pinned = False

    def show_ui(self):
        if self.is_ui_open:
            return

        self.is_ui_open = True
        self.ui_window = tk.Toplevel()
        self.ui_window.title("Clipboard")
        self.ui_window.overrideredirect(True)
        self.ui_window.attributes('-topmost', True)

        bg_color = "#ffffff"
        hover_color = "#f3f3f3"
        select_color = "#8fa876"
        border_color = "#e0e0e0"
        text_color = "#1f1f1f"
        secondary_text = "#707070"

        width = 400
        max_height = 500

        # Position near mouse
        try:
            from pynput.mouse import Controller as MouseController
            mouse = MouseController()
            mx, my = mouse.position
            screen_width = self.ui_window.winfo_screenwidth()
            screen_height = self.ui_window.winfo_screenheight()
            x = min(max(mx - width // 2, 0), screen_width - width)
            y = min(max(my + 20, 0), screen_height - max_height)
        except:
            x, y = 100, 100

        main_frame = tk.Frame(self.ui_window, bg=bg_color,
                             highlightbackground=border_color,
                             highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Draggable header
        header = tk.Frame(main_frame, bg=bg_color, height=40, cursor="fleur")
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        header.pack_propagate(False)

        self._drag_data = {"x": 0, "y": 0}
        def start_drag(event):
            self._drag_data["x"] = event.x_root - self.ui_window.winfo_x()
            self._drag_data["y"] = event.y_root - self.ui_window.winfo_y()

        def do_drag(event):
            x = event.x_root - self._drag_data["x"]
            y = event.y_root - self._drag_data["y"]
            self.ui_window.geometry(f"+{x}+{y}")

        header.bind("<Button-1>", start_drag)
        header.bind("<B1-Motion>", do_drag)

        title_font = font.Font(family="Ubuntu", size=11, weight="bold")
        title_label = tk.Label(header, text="📋 Clipboard",
                              font=title_font, bg=bg_color, fg=text_color)
        title_label.pack(side=tk.LEFT, pady=5)

        pin_btn = tk.Label(header, text="📌", font=("Ubuntu", 14),
                          bg=bg_color, fg=secondary_text, cursor="hand2")
        pin_btn.pack(side=tk.RIGHT, padx=5)

        def toggle_pin(e):
            self.pinned = not self.pinned
            pin_btn.config(text="📍" if self.pinned else "📌")

        pin_btn.bind("<Button-1>", toggle_pin)

        # Search
        search_frame = tk.Frame(main_frame, bg=bg_color)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=("Ubuntu", 10), relief=tk.FLAT,
                               bg="#f5f5f5", fg=secondary_text)
        search_entry.pack(fill=tk.X, ipady=6, padx=2, pady=2)
        search_entry.insert(0, "🔍 Search clipboard...")

        def on_focus_in(e):
            if search_entry.get() == "🔍 Search clipboard...":
                search_entry.delete(0, tk.END)
                search_entry.config(fg=text_color)

        def on_focus_out(e):
            if not search_entry.get():
                search_entry.insert(0, "🔍 Search clipboard...")
                search_entry.config(fg=secondary_text)

        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)

        separator = tk.Frame(main_frame, bg=border_color, height=1)
        separator.pack(fill=tk.X, padx=10)

        # Scrollable area
        canvas_frame = tk.Frame(main_frame, bg=bg_color)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, bg=bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=bg_color)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        item_frames = []
        selected_index = [0]

        def select_item(idx):
            for i, frame in enumerate(item_frames):
                is_selected = (i == idx)
                color = select_color if is_selected else bg_color
                fg = "white" if is_selected else text_color
                frame.config(bg=color)
                for child in frame.winfo_children():
                    child.config(bg=color)
                    if isinstance(child, tk.Label):
                        child.config(fg=fg)
                    for grand in child.winfo_children():
                        grand.config(bg=color)
                        if isinstance(grand, tk.Label):
                            grand.config(fg=fg)
            selected_index[0] = idx

        def paste_item(idx):
            if 0 <= idx < len(self.clip_history):
                actual_idx = len(self.clip_history) - 1 - idx
                text = list(self.clip_history)[actual_idx]
                self.close_ui()
                time.sleep(0.05)
                if self.auto_paste:
                    self.paste_text(text)
                else:
                    pc.copy(text)

        # Populate items
        if not self.clip_history:
            tk.Label(scrollable_frame, text="No clipboard history yet", bg=bg_color, fg=secondary_text).pack(pady=50)
        else:
            for i, item in enumerate(reversed(list(self.clip_history))):
                item_frame = tk.Frame(scrollable_frame, bg=bg_color, cursor="hand2")
                item_frame.pack(fill=tk.X, pady=2)
                item_frames.append(item_frame)

                inner = tk.Frame(item_frame, bg=bg_color)
                inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

                preview = item.replace('\n', ' ').strip()
                if len(preview) > 80:
                    preview = preview[:80] + '...'

                text_label = tk.Label(inner, text=preview, font=("Ubuntu", 10),
                                     bg=bg_color, fg=text_color, anchor="w")
                text_label.pack(fill=tk.X)

                # Type
                if item.startswith(('http://', 'https://')):
                    typ = "🔗 Link"
                elif item.replace('.','').replace('-','').isdigit():
                    typ = "🔢 Number"
                elif '\n' in item:
                    typ = f"📄 {len(item.split())} words"
                else:
                    typ = "Text"

                type_label = tk.Label(inner, text=typ, font=("Ubuntu", 8),
                                     bg=bg_color, fg=secondary_text, anchor="w")
                type_label.pack(fill=tk.X)

                # Click handler
                def make_click_handler(idx):
                    return lambda e: paste_item(idx)

                item_frame.bind("<Button-1>", make_click_handler(i))
                inner.bind("<Button-1>", make_click_handler(i))
                text_label.bind("<Button-1>", make_click_handler(i))
                type_label.bind("<Button-1>", make_click_handler(i))

                # Hover
                def make_enter_handler(idx):
                    return lambda e: (
                        item_frame.config(bg=hover_color),
                        inner.config(bg=hover_color),
                        text_label.config(bg=hover_color),
                        type_label.config(bg=hover_color)
                    ) if selected_index[0] != idx else None

                def make_leave_handler(idx):
                    return lambda e: (
                        item_frame.config(bg=bg_color),
                        inner.config(bg=bg_color),
                        text_label.config(bg=bg_color),
                        type_label.config(bg=bg_color)
                    ) if selected_index[0] != idx else None

                item_frame.bind("<Enter>", make_enter_handler(i))
                item_frame.bind("<Leave>", make_leave_handler(i))

        # Keyboard handling — bound ONLY to ui_window
        def on_key(event):
            if not item_frames:
                return
            if event.keysym == "Down":
                select_item(min(selected_index[0] + 1, len(item_frames) - 1))
            elif event.keysym == "Up":
                select_item(max(selected_index[0] - 1, 0))
            elif event.keysym == "Return":
                paste_item(selected_index[0])
            elif event.keysym == "Escape":
                if not self.pinned:
                    self.close_ui()
            elif event.keysym == "Delete":
                if 0 <= selected_index[0] < len(self.clip_history):
                    actual_idx = len(self.clip_history) - 1 - selected_index[0]
                    text_to_remove = list(self.clip_history)[actual_idx]
                    self.clip_history.remove(text_to_remove)
                    self.save_config()
                    self.close_ui()
                    self.show_ui()

        self.ui_window.bind("<Key>", on_key)
        self.ui_window.focus_set()
        self.ui_window.grab_set()  # Modal-like behavior

        # Search
        def on_search_change(*_):
            query = search_var.get().lower()
            if query in ("", "🔍 search clipboard..."):
                for f in item_frames:
                    f.pack(fill=tk.X, pady=2)
                return
            for i, (frame, item) in enumerate(zip(item_frames, reversed(list(self.clip_history)))):
                frame.pack(fill=tk.X, pady=2) if query in item.lower() else frame.pack_forget()

        search_var.trace("w", on_search_change)

        # Footer
        footer = tk.Frame(main_frame, bg=bg_color, height=30)
        footer.pack(fill=tk.X, padx=10, pady=(5, 10))
        info = f"{len(self.clip_history)} items • ↑↓ Enter Del"
        tk.Label(footer, text=info, font=("Ubuntu", 8), bg=bg_color, fg=secondary_text).pack()

        # Finalize
        items_height = min(len(item_frames) * 70, 400)
        total_height = min(items_height + 150, max_height)
        self.ui_window.geometry(f"{width}x{total_height}+{x}+{y}")

        if item_frames:
            select_item(0)

    def stop(self):
        self.running = False
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        self.save_config()


if __name__ == "__main__":
    try:
        manager = ClipboardManager()
        while True:
            try:
                manager.root.update()
            except tk.TclError:
                break

            if manager.needs_show_ui:
                manager.needs_show_ui = False
                manager.toggle_ui()

            if manager.needs_paste_latest:
                manager.needs_paste_latest = False
                manager.paste_latest()

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n👋 Stopped")
        manager.stop()
        sys.exit(0)