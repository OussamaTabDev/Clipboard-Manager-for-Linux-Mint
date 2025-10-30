#!/usr/bin/env python3
"""
Clipboard Manager for Linux Mint
Features:
- Super+V to open clipboard history
- Click to paste automatically
- Settings: auto-paste, max size, clear history
- Mint-style UI with clean design
"""

import pyperclip as pc
from collections import deque
import time
import threading
import tkinter as tk
from tkinter import ttk, font
# import keyboard
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
        
        # Load config
        self.load_config()
        
        # Start clipboard monitoring
        self.monitor_thread = threading.Thread(target=self.watch_clipboard, daemon=True)
        self.monitor_thread.start()
        
        # Setup hotkey using pynput (NO ROOT NEEDED!)
        self.hotkey_listener = pynput_kb.GlobalHotKeys({
            '<cmd>+v': self.show_ui
        })
        self.hotkey_listener.start()
        
        print("🚀 Clipboard Manager Started")
        print("   Press Super+V to open history")
        print("   Press Ctrl+C to exit\n")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.max_size = config.get('max_size', 100)
                    self.auto_paste = config.get('auto_paste', True)
                    self.clip_history = deque(config.get('history', []), maxlen=self.max_size)
                    print(f"✅ Config loaded: max_size={self.max_size}, auto_paste={self.auto_paste}")
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
                print(f"⚠️ Clipboard error: {e}")
            
            time.sleep(0.3)
    
    def paste_text(self, text):
        """Paste text using keyboard simulation"""
        # Copy to clipboard
        pc.copy(text)
        time.sleep(0.05)
        
        # Simulate Ctrl+V
        self.keyboard_controller.press(Key.ctrl)
        self.keyboard_controller.press('v')
        self.keyboard_controller.release('v')
        self.keyboard_controller.release(Key.ctrl)
    
    def show_ui(self):
        """Show the clipboard history UI"""
        if self.ui_window and tk.Toplevel.winfo_exists(self.ui_window):
            self.ui_window.lift()
            return
        
        self.ui_window = tk.Tk()
        self.ui_window.title("Clipboard History")
        self.ui_window.geometry("650x500")
        
        # Mint green accent color
        mint_green = "#8fa876"
        bg_color = "#f5f5f5"
        header_bg = "#e8e8e8"
        
        self.ui_window.configure(bg=bg_color)
        
        # Center window on screen
        self.ui_window.update_idletasks()
        x = (self.ui_window.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.ui_window.winfo_screenheight() // 2) - (500 // 2)
        self.ui_window.geometry(f"650x500+{x}+{y}")
        
        # Header
        header = tk.Frame(self.ui_window, bg=header_bg, height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        title_font = font.Font(family="Ubuntu", size=14, weight="bold")
        title_label = tk.Label(header, text="📋 Clipboard History", 
                              font=title_font, bg=header_bg, fg="#2d2d2d")
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Settings button
        settings_btn = tk.Button(header, text="⚙️ Settings", 
                                font=("Ubuntu", 10),
                                bg=mint_green, fg="white",
                                relief=tk.FLAT, padx=15, pady=5,
                                cursor="hand2",
                                command=self.show_settings)
        settings_btn.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Clear button
        clear_btn = tk.Button(header, text="🗑️ Clear All", 
                             font=("Ubuntu", 10),
                             bg="#d9534f", fg="white",
                             relief=tk.FLAT, padx=15, pady=5,
                             cursor="hand2",
                             command=lambda: self.clear_history_ui(listbox))
        clear_btn.pack(side=tk.RIGHT, padx=5, pady=15)
        
        # Info label
        info_frame = tk.Frame(self.ui_window, bg=bg_color)
        info_frame.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        info_text = f"Click to {'paste automatically' if self.auto_paste else 'copy'} • {len(self.clip_history)} items • Max: {self.max_size}"
        info_label = tk.Label(info_frame, text=info_text, 
                             font=("Ubuntu", 9), bg=bg_color, fg="#666")
        info_label.pack(side=tk.LEFT)
        
        # Scrollable list frame
        list_frame = tk.Frame(self.ui_window, bg=bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 20))
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox
        listbox_font = font.Font(family="Ubuntu Mono", size=10)
        listbox = tk.Listbox(list_frame, 
                            font=listbox_font,
                            bg="white",
                            fg="#2d2d2d",
                            selectbackground=mint_green,
                            selectforeground="white",
                            relief=tk.FLAT,
                            borderwidth=1,
                            highlightthickness=1,
                            highlightbackground="#ccc",
                            yscrollcommand=scrollbar.set,
                            activestyle='none')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate list (most recent first)
        for item in reversed(list(self.clip_history)):
            preview = item.replace('\n', ' ').replace('\r', '')
            preview = (preview[:100] + '...') if len(preview) > 100 else preview
            listbox.insert(tk.END, preview)
        
        # Bind selection
        def on_select(event):
            if listbox.curselection():
                index = listbox.curselection()[0]
                # Reverse index since we reversed the display
                actual_index = len(self.clip_history) - 1 - index
                selected_text = list(self.clip_history)[actual_index]
                
                if self.auto_paste:
                    self.ui_window.destroy()
                    time.sleep(0.1)
                    self.paste_text(selected_text)
                    print(f"📋 Pasted: {selected_text[:50]}...")
                else:
                    pc.copy(selected_text)
                    self.ui_window.destroy()
                    print(f"📋 Copied: {selected_text[:50]}...")
        
        listbox.bind('<<ListboxSelect>>', on_select)
        
        # Keyboard shortcuts
        def on_escape(event):
            self.ui_window.destroy()
        
        self.ui_window.bind('<Escape>', on_escape)
        
        # Focus and select first item
        listbox.focus_set()
        if listbox.size() > 0:
            listbox.selection_set(0)
        
        self.ui_window.mainloop()
    
    def show_settings(self):
        """Show settings dialog"""
        settings_win = tk.Toplevel()
        settings_win.title("Settings")
        settings_win.geometry("400x300")
        settings_win.configure(bg="#f5f5f5")
        settings_win.transient(self.ui_window)
        settings_win.grab_set()
        
        # Center on parent
        settings_win.update_idletasks()
        x = self.ui_window.winfo_x() + (self.ui_window.winfo_width() // 2) - 200
        y = self.ui_window.winfo_y() + (self.ui_window.winfo_height() // 2) - 150
        settings_win.geometry(f"400x300+{x}+{y}")
        
        mint_green = "#8fa876"
        
        # Title
        title = tk.Label(settings_win, text="⚙️ Settings", 
                        font=("Ubuntu", 14, "bold"),
                        bg="#f5f5f5", fg="#2d2d2d")
        title.pack(pady=20)
        
        # Auto-paste setting
        auto_paste_var = tk.BooleanVar(value=self.auto_paste)
        auto_paste_check = tk.Checkbutton(settings_win,
                                         text="Paste automatically on selection",
                                         variable=auto_paste_var,
                                         font=("Ubuntu", 11),
                                         bg="#f5f5f5",
                                         activebackground="#f5f5f5",
                                         selectcolor="white")
        auto_paste_check.pack(pady=10, padx=30, anchor=tk.W)
        
        # Max size setting
        size_frame = tk.Frame(settings_win, bg="#f5f5f5")
        size_frame.pack(pady=10, padx=30, fill=tk.X)
        
        size_label = tk.Label(size_frame, text="Maximum history size:",
                             font=("Ubuntu", 11),
                             bg="#f5f5f5", fg="#2d2d2d")
        size_label.pack(side=tk.LEFT)
        
        size_var = tk.IntVar(value=self.max_size)
        size_entry = tk.Entry(size_frame, textvariable=size_var,
                             font=("Ubuntu", 11), width=10)
        size_entry.pack(side=tk.LEFT, padx=10)
        
        # Save button
        def save_settings():
            self.auto_paste = auto_paste_var.get()
            new_size = size_var.get()
            
            if new_size > 0:
                self.max_size = new_size
                self.clip_history = deque(self.clip_history, maxlen=self.max_size)
                self.save_config()
                print(f"✅ Settings saved: max_size={self.max_size}, auto_paste={self.auto_paste}")
                settings_win.destroy()
            else:
                error_label = tk.Label(settings_win, text="Max size must be > 0",
                                      font=("Ubuntu", 9),
                                      bg="#f5f5f5", fg="#d9534f")
                error_label.pack(pady=5)
        
        save_btn = tk.Button(settings_win, text="Save Settings",
                            font=("Ubuntu", 11, "bold"),
                            bg=mint_green, fg="white",
                            relief=tk.FLAT, padx=30, pady=10,
                            cursor="hand2",
                            command=save_settings)
        save_btn.pack(pady=30)
    
    def clear_history_ui(self, listbox):
        """Clear history and update UI"""
        self.clip_history.clear()
        self.save_config()
        listbox.delete(0, tk.END)
        print("🗑️ History cleared")
    
    def stop(self):
        self.running = False
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        self.save_config()


if __name__ == "__main__":
    try:
        manager = ClipboardManager()
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Clipboard Manager stopped")
        manager.stop()