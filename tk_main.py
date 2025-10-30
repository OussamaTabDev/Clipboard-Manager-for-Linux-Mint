#!/usr/bin/env python3
"""
Clipboard Manager for Linux Mint (Windows 11 Style)
Features:
- Ctrl+Alt+V to toggle clipboard history (Linux-compatible hotkey)
- Arrow keys + Enter to select
- Mouse click to paste
- Always on top, auto-closes when clicking outside
- Compact, modern design
"""

import pyperclip as pc
from collections import deque
import time
import threading
import tkinter as tk
from tkinter import ttk, font
from pynput import keyboard as pynput_kb
from pynput.keyboard import Controller, Key
import json
import os

# Configuration file
CONFIG_FILE = os.path.expanduser("~/.clipboard_manager_config.json")

class ClipboardManager:

    def __init__(self):
        self.max_size = 100
        self.auto_paste = True
        self.clip_history = deque(maxlen=self.max_size)
        self.initial_clipboard = ""
        self.last_saved = ""
        self.running = True
        self.keyboard_controller = Controller()
        self.ui_window = None
        self.is_ui_open = False

        # Thread-safe request flags (pynput callback -> set flag -> main thread handles)
        self.needs_show_ui = False
        self.needs_paste_latest = False

        # Create a hidden Tk root (must be created in main thread)
        # we withdraw it so no unwanted empty window appears
        self.root = tk.Tk()
        self.root.withdraw()

        # Load config
        self.load_config()

        # Start clipboard monitoring
        self.monitor_thread = threading.Thread(target=self.watch_clipboard, daemon=True)
        self.monitor_thread.start()

        # Setup hotkeys: callbacks only set flags (safe to call from pynput thread)
        def _request_show_ui():
            self.needs_show_ui = True

        def _request_paste_latest():
            self.needs_paste_latest = True

        # Use Linux-compatible hotkeys (Ctrl+Alt combinations work reliably on Linux)
        try:
            # self.hotkey_listener = pynput_kb.GlobalHotKeys({
            #     '<ctrl>+<alt>+v': _request_show_ui,  # Primary hotkey for Linux
            #     '<ctrl>+<shift>+v': _request_paste_latest,  # Paste latest
            # })
            self.hotkey_listener = pynput_kb.GlobalHotKeys({
                '<cmd>+v': _request_show_ui,  # Primary hotkey for Linux
                '<cmd>+<shift>+v': _request_paste_latest,  # Paste latest
            })
            self.hotkey_listener.start()
            print("🚀 Clipboard Manager Started (Linux Edition)")
            print("   Press Ctrl+Alt+V to toggle history")
            print("   Press Ctrl+Shift+V to paste latest")
            print("   Use Arrow Keys + Enter to select")
            print("   Press Ctrl+C to exit\n")
        except Exception as e:
            print(f"⚠️ Warning: Could not set up global hotkeys: {e}")
            print("   You can still use the clipboard manager programmatically")

    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.max_size = config.get('max_size', 100)
                    self.auto_paste = config.get('auto_paste', True)
                    self.clip_history = deque(config.get('history', []), maxlen=self.max_size)
                    print(f"✅ Config loaded: {len(self.clip_history)} items")
        except Exception as e:
            print(f"⚠️ Config load error: {e}")
    
    def save_config(self):
        """Save configuration to file"""
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
        """Monitor clipboard for changes"""
        try:
            self.initial_clipboard = pc.paste()
        except:
            self.initial_clipboard = ""
        
        self.last_saved = self.initial_clipboard
        
        while self.running:
            try:
                current = pc.paste()
                
                if current and current != self.last_saved:
                    if current not in self.clip_history:
                        self.clip_history.append(current)
                        preview = (current[:47] + '...') if len(current) > 50 else current
                        print(f"✅ Saved: {repr(preview)}")
                        self.save_config()
                    self.last_saved = current
            except Exception as e:
                pass  # Silent fail for clipboard errors
            
            time.sleep(0.3)
    
    def paste_text(self, text):
        """Paste text using keyboard simulation (robust on Linux)."""
        # copy to clipboard first
        pc.copy(text)

        # small delay to give the OS clipboard time to update
        time.sleep(0.08)

        # Press and hold Ctrl (use left ctrl which tends to be reliable)
        try:
            self.keyboard_controller.press(Key.ctrl_l)
            # small pause to ensure the modifier is registered before sending 'v'
            time.sleep(0.04)
            # send 'v'
            self.keyboard_controller.press('v')
            self.keyboard_controller.release('v')
            # release ctrl
            self.keyboard_controller.release(Key.ctrl_l)
        except Exception:
            # best-effort fallback: try Ctrl+Shift+V (used by some terminals)
            try:
                self.keyboard_controller.press(Key.ctrl_l)
                self.keyboard_controller.press(Key.shift)
                time.sleep(0.03)
                self.keyboard_controller.press('v')
                self.keyboard_controller.release('v')
                self.keyboard_controller.release(Key.shift)
                self.keyboard_controller.release(Key.ctrl_l)
            except Exception:
                # last fallback: just leave text in clipboard (user can manually paste)
                pass

    def paste_latest(self):
        """Paste the most recent clipboard item"""
        if self.clip_history:
            latest = list(self.clip_history)[-1]
            self.paste_text(latest)
            print(f"📋 Pasted latest: {latest[:50]}...")
        else:
            print("⚠️ No clipboard history available")
    
    def toggle_ui(self):
        """Toggle clipboard UI visibility"""
        if self.is_ui_open and self.ui_window:
            self.close_ui()
        else:
            self.show_ui()
    
    def close_ui(self):
        """Close the UI window"""
        if self.ui_window:
            try:
                self.ui_window.destroy()
            except:
                pass
            self.ui_window = None
            self.is_ui_open = False
    
    def show_ui(self):
        """Show the clipboard history UI (Windows 11 style)"""
        if self.is_ui_open:
            return
        
        self.is_ui_open = True
        self.ui_window = tk.Toplevel()
        self.ui_window.title("Clipboard")
        
        # Remove window decorations but keep it functional
        self.ui_window.overrideredirect(True)
        
        # Colors (Windows 11 inspired with Mint accent)
        bg_color = "#ffffff"
        hover_color = "#f3f3f3"
        select_color = "#8fa876"  # Mint green
        border_color = "#e0e0e0"
        text_color = "#1f1f1f"
        secondary_text = "#707070"
        
        # Window setup
        width = 400
        max_height = 500
        
        # Position near cursor (top-right area like Windows)
        screen_width = self.ui_window.winfo_screenwidth()
        screen_height = self.ui_window.winfo_screenheight()
        x = screen_width - width - 100
        y = 100
        
        # Main container with shadow effect
        self.ui_window.configure(bg=border_color)
        
        main_frame = tk.Frame(self.ui_window, bg=bg_color, 
                             highlightbackground=border_color,
                             highlightthickness=1)
        main_frame.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)
        
        # Header with search and settings
        header = tk.Frame(main_frame, bg=bg_color, height=50)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        header.pack_propagate(False)
        
        # Title
        title_font = font.Font(family="Ubuntu", size=11, weight="bold")
        title_label = tk.Label(header, text="📋 Clipboard", 
                              font=title_font, bg=bg_color, fg=text_color)
        title_label.pack(side=tk.LEFT, pady=10)
        
        # Settings icon (gear)
        settings_btn = tk.Label(header, text="⚙️", font=("Ubuntu", 14),
                               bg=bg_color, fg=secondary_text, cursor="hand2")
        settings_btn.pack(side=tk.RIGHT, padx=5, pady=10)
        settings_btn.bind("<Button-1>", lambda e: self.show_settings_compact())
        
        # Pin icon (to keep open)
        pin_btn = tk.Label(header, text="📌", font=("Ubuntu", 14),
                          bg=bg_color, fg=secondary_text, cursor="hand2")
        pin_btn.pack(side=tk.RIGHT, padx=5, pady=10)
        
        pinned = [False]
        def toggle_pin(e):
            pinned[0] = not pinned[0]
            pin_btn.config(text="📍" if pinned[0] else "📌")
        pin_btn.bind("<Button-1>", toggle_pin)
        
        # Search box
        search_frame = tk.Frame(main_frame, bg=bg_color)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=("Ubuntu", 10), relief=tk.FLAT,
                               bg="#f5f5f5", fg=text_color,
                               insertbackground=text_color)
        search_entry.pack(fill=tk.X, ipady=6, padx=2, pady=2)
        search_entry.insert(0, "🔍 Search clipboard...")
        search_entry.config(fg=secondary_text)
        
        def on_search_focus(e):
            if search_entry.get() == "🔍 Search clipboard...":
                search_entry.delete(0, tk.END)
                search_entry.config(fg=text_color)
        
        def on_search_unfocus(e):
            if not search_entry.get():
                search_entry.insert(0, "🔍 Search clipboard...")
                search_entry.config(fg=secondary_text)
        
        search_entry.bind("<FocusIn>", on_search_focus)
        search_entry.bind("<FocusOut>", on_search_unfocus)
        
        # Separator
        separator = tk.Frame(main_frame, bg=border_color, height=1)
        separator.pack(fill=tk.X, padx=10)
        
        # Canvas for items (allows custom styling)
        canvas_frame = tk.Frame(main_frame, bg=bg_color)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg=bg_color, 
                          highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg=bg_color)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store item frames for keyboard navigation
        item_frames = []
        selected_index = [0]
        
        def select_item(index):
            """Highlight selected item"""
            for i, frame in enumerate(item_frames):
                if i == index:
                    frame.config(bg=select_color)
                    for child in frame.winfo_children():
                        child.config(bg=select_color)
                        if isinstance(child, (tk.Label, tk.Button)):
                            child.config(fg="white")
                        for grandchild in child.winfo_children():
                            grandchild.config(bg=select_color)
                            if isinstance(grandchild, (tk.Label, tk.Button)):
                                grandchild.config(fg="white")
                else:
                    frame.config(bg=bg_color)
                    for child in frame.winfo_children():
                        child.config(bg=bg_color)
                        if isinstance(child, (tk.Label, tk.Button)):
                            child.config(fg=text_color)
                        for grandchild in child.winfo_children():
                            grandchild.config(bg=bg_color)
                            if isinstance(grandchild, (tk.Label, tk.Button)):
                                grandchild.config(fg=text_color)
            selected_index[0] = index
        
        def paste_item(index):
            """Paste selected item"""
            if 0 <= index < len(self.clip_history):
                actual_index = len(self.clip_history) - 1 - index
                selected_text = list(self.clip_history)[actual_index]
                
                self.close_ui()
                time.sleep(0.1)
                
                if self.auto_paste:
                    self.paste_text(selected_text)
                    print(f"📋 Pasted: {selected_text[:50]}...")
                else:
                    pc.copy(selected_text)
                    print(f"📋 Copied: {selected_text[:50]}...")
        
        # Populate items
        if not self.clip_history:
            empty_label = tk.Label(scrollable_frame, 
                                  text="No clipboard history yet\nCopy something to get started",
                                  font=("Ubuntu", 10), bg=bg_color, 
                                  fg=secondary_text, justify=tk.CENTER)
            empty_label.pack(pady=50)
        else:
            for i, item in enumerate(reversed(list(self.clip_history))):
                # Item frame
                item_frame = tk.Frame(scrollable_frame, bg=bg_color, 
                                     cursor="hand2")
                item_frame.pack(fill=tk.X, pady=2)
                item_frames.append(item_frame)
                
                # Item content
                item_inner = tk.Frame(item_frame, bg=bg_color)
                item_inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
                
                # Preview text
                preview = item.replace('\n', ' ').replace('\r', '').strip()
                preview = (preview[:80] + '...') if len(preview) > 80 else preview
                
                text_label = tk.Label(item_inner, text=preview,
                                     font=("Ubuntu", 10), bg=bg_color,
                                     fg=text_color, anchor="w", justify=tk.LEFT)
                text_label.pack(fill=tk.X)
                
                # Type indicator (text/number/url)
                item_type = "Text"
                if item.startswith(('http://', 'https://')):
                    item_type = "🔗 Link"
                elif item.replace('.','').replace('-','').isdigit():
                    item_type = "🔢 Number"
                elif '\n' in item:
                    item_type = f"📄 {len(item.split())} words"
                
                type_label = tk.Label(item_inner, text=item_type,
                                     font=("Ubuntu", 8), bg=bg_color,
                                     fg=secondary_text, anchor="w")
                type_label.pack(fill=tk.X)
                
                # Hover effect
                def on_enter(e, frame=item_frame, idx=i):
                    if selected_index[0] != idx:
                        frame.config(bg=hover_color)
                        for child in frame.winfo_children():
                            child.config(bg=hover_color)
                            for subchild in child.winfo_children():
                                subchild.config(bg=hover_color)
                
                def on_leave(e, frame=item_frame, idx=i):
                    if selected_index[0] != idx:
                        frame.config(bg=bg_color)
                        for child in frame.winfo_children():
                            child.config(bg=bg_color)
                            for subchild in child.winfo_children():
                                subchild.config(bg=bg_color)
                
                def on_click(e, idx=i):
                    paste_item(idx)
                
                item_frame.bind("<Enter>", on_enter)
                item_frame.bind("<Leave>", on_leave)
                item_frame.bind("<Button-1>", on_click)
                item_inner.bind("<Button-1>", on_click)
                text_label.bind("<Button-1>", on_click)
                type_label.bind("<Button-1>", on_click)
        
        # Keyboard navigation
        def on_key(event):
            if not item_frames:
                return
            
            if event.keysym == "Down":
                new_index = min(selected_index[0] + 1, len(item_frames) - 1)
                select_item(new_index)
            elif event.keysym == "Up":
                new_index = max(selected_index[0] - 1, 0)
                select_item(new_index)
            elif event.keysym == "Return":
                paste_item(selected_index[0])
            elif event.keysym == "Escape":
                if not pinned[0]:
                    self.close_ui()
            elif event.keysym == "Delete":
                # Delete selected item
                if 0 <= selected_index[0] < len(self.clip_history):
                    actual_index = len(self.clip_history) - 1 - selected_index[0]
                    deleted = list(self.clip_history)[actual_index]
                    temp_list = list(self.clip_history)
                    temp_list.remove(deleted)
                    self.clip_history = deque(temp_list, maxlen=self.max_size)
                    self.save_config()
                    self.close_ui()
                    self.show_ui()
        
        self.ui_window.bind("<Key>", on_key)
        
        # Search functionality
        def on_search_change(*args):
            query = search_var.get().lower()
            if query == "🔍 search clipboard...":
                return
            
            for i, (frame, item) in enumerate(zip(item_frames, reversed(list(self.clip_history)))):
                if query in item.lower():
                    frame.pack(fill=tk.X, pady=2)
                else:
                    frame.pack_forget()
        
        search_var.trace("w", on_search_change)
        
        # Click outside to close
        def check_focus():
            if not pinned[0] and self.ui_window:
                try:
                    if not self.ui_window.focus_displayof():
                        self.close_ui()
                        return
                except:
                    pass
                self.ui_window.after(500, check_focus)
        
        # Footer with info
        footer = tk.Frame(main_frame, bg=bg_color, height=30)
        footer.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        info_text = f"{len(self.clip_history)} items • ↑↓ Navigate • Enter to paste • Del to remove"
        info_label = tk.Label(footer, text=info_text, 
                             font=("Ubuntu", 8), bg=bg_color, fg=secondary_text)
        info_label.pack()
        
        # Calculate actual height based on items
        items_height = min(len(item_frames) * 70, 400)
        total_height = min(items_height + 150, max_height)
        
        self.ui_window.geometry(f"{width}x{total_height}+{x}+{y}")
        
        # Always on top
        self.ui_window.attributes('-topmost', True)
        
        # Focus window
        self.ui_window.focus_force()
        
        # Select first item
        if item_frames:
            select_item(0)
        
        # Start focus checker
        self.ui_window.after(500, check_focus)
    
    def show_settings_compact(self):
        """Show compact settings menu"""
        settings_win = tk.Toplevel()
        settings_win.title("Settings")
        settings_win.overrideredirect(True)
        settings_win.configure(bg="#ffffff")
        settings_win.attributes('-topmost', True)
        
        # Position near main window
        if self.ui_window:
            x = self.ui_window.winfo_x() - 250
            y = self.ui_window.winfo_y()
            settings_win.geometry(f"240x200+{x}+{y}")
        
        frame = tk.Frame(settings_win, bg="#ffffff", 
                        highlightbackground="#e0e0e0", highlightthickness=1)
        frame.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)
        
        # Title
        title = tk.Label(frame, text="⚙️ Settings", 
                        font=("Ubuntu", 11, "bold"),
                        bg="#ffffff", fg="#1f1f1f")
        title.pack(pady=10)
        
        # Auto-paste
        auto_paste_var = tk.BooleanVar(value=self.auto_paste)
        check1 = tk.Checkbutton(frame, text="Auto-paste on select",
                               variable=auto_paste_var,
                               font=("Ubuntu", 9),
                               bg="#ffffff", activebackground="#ffffff")
        check1.pack(pady=5, padx=20, anchor=tk.W)
        
        # Max size
        size_frame = tk.Frame(frame, bg="#ffffff")
        size_frame.pack(pady=5, padx=20, fill=tk.X)
        
        tk.Label(size_frame, text="Max items:", font=("Ubuntu", 9),
                bg="#ffffff").pack(side=tk.LEFT)
        
        size_var = tk.IntVar(value=self.max_size)
        size_entry = tk.Entry(size_frame, textvariable=size_var,
                             font=("Ubuntu", 9), width=8)
        size_entry.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg="#ffffff")
        btn_frame.pack(pady=15)
        
        def save():
            self.auto_paste = auto_paste_var.get()
            self.max_size = size_var.get()
            self.clip_history = deque(self.clip_history, maxlen=self.max_size)
            self.save_config()
            settings_win.destroy()
        
        def clear_all():
            self.clip_history.clear()
            self.save_config()
            settings_win.destroy()
            self.close_ui()
        
        tk.Button(btn_frame, text="💾 Save", command=save,
                 font=("Ubuntu", 9), bg="#8fa876", fg="white",
                 relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🗑️ Clear All", command=clear_all,
                 font=("Ubuntu", 9), bg="#d9534f", fg="white",
                 relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Close on focus loss
        def check_focus():
            try:
                if not settings_win.focus_displayof():
                    settings_win.destroy()
                    return
            except:
                return
            settings_win.after(500, check_focus)
        
        settings_win.after(500, check_focus)
    
    def stop(self):
        self.running = False
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        self.save_config()


if __name__ == "__main__":
    try:
        manager = ClipboardManager()

        # Simple main loop that keeps everything on the main thread
        # Poll flags set by pynput callbacks and call UI/paste functions from main thread.
        while True:
            # process any pending tkinter events (keeps UI responsive)
            try:
                manager.root.update_idletasks()
                manager.root.update()
            except tk.TclError:
                # if the root was destroyed or there's an error, stop
                break

            # handle requests from hotkey callbacks
            if manager.needs_show_ui:
                manager.needs_show_ui = False
                # toggle UI (calling from main thread)
                manager.toggle_ui()

            if manager.needs_paste_latest:
                manager.needs_paste_latest = False
                manager.paste_latest()

            # small sleep so this loop isn't busy-waiting
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n👋 Clipboard Manager stopped")
        manager.stop()

# ---
# it's working , but bad , if i click cmd + v paste direcly , that not the this need to happen , need to select by mouse or arrows and  enter ,
# i can't move the clip board ui by mouse
# the original place that clipboard to apear is bottom of the line that i write on it 
# if i click any place except  ui , should ui hide , 
# arrows and typing in the search not working i guess beacuse is not in top , like not the hightlited one 
# if clciked cmd + v show me ui but in the same time paste , but not that what need , just paste after clicking the selection 