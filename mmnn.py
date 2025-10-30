#!/usr/bin/env python3
"""
Clipboard Manager for Linux (Windows 11 Style) - Qt6 Version
Smooth dragging, proper focus handling, and modern UI
"""

import sys
import json
import os
from collections import deque
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QLineEdit, QScrollArea, 
                              QFrame, QPushButton)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor, QKeySequence, QShortcut
import pyperclip as pc
from pynput import keyboard as pynput_kb
from pynput.keyboard import Controller, Key

CONFIG_FILE = os.path.expanduser("~/.clipboard_manager_config.json")


class ClipboardItem(QFrame):
    """Individual clipboard item widget"""
    clicked = pyqtSignal(int)
    
    def __init__(self, text, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.text = text
        self.is_selected = False
        
        self.setFixedHeight(70)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("QFrame { background: white; border-radius: 4px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # Preview text
        preview = text.replace('\n', ' ').strip()
        if len(preview) > 80:
            preview = preview[:80] + '...'
            
        self.text_label = QLabel(preview)
        self.text_label.setFont(QFont("Ubuntu", 10))
        self.text_label.setStyleSheet("color: #1f1f1f;")
        layout.addWidget(self.text_label)
        
        # Type indicator
        if text.startswith(('http://', 'https://')):
            typ = "🔗 Link"
        elif text.replace('.','').replace('-','').isdigit():
            typ = "🔢 Number"
        elif '\n' in text:
            typ = f"📄 {len(text.split())} words"
        else:
            typ = "📝 Text"
            
        self.type_label = QLabel(typ)
        self.type_label.setFont(QFont("Ubuntu", 8))
        self.type_label.setStyleSheet("color: #707070;")
        layout.addWidget(self.type_label)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
            
    def enterEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet("QFrame { background: #f3f3f3; border-radius: 4px; }")
            
    def leaveEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet("QFrame { background: white; border-radius: 4px; }")
            
    def set_selected(self, selected):
        self.is_selected = selected
        if selected:
            self.setStyleSheet("QFrame { background: #8fa876; border-radius: 4px; }")
            self.text_label.setStyleSheet("color: white;")
            self.type_label.setStyleSheet("color: white;")
        else:
            self.setStyleSheet("QFrame { background: white; border-radius: 4px; }")
            self.text_label.setStyleSheet("color: #1f1f1f;")
            self.type_label.setStyleSheet("color: #707070;")


class ClipboardUI(QMainWindow):
    """Modern clipboard manager UI"""
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.selected_index = 0
        self.drag_position = QPoint()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setup_ui()
        self.position_near_cursor()
        
    def setup_ui(self):
        # Main container
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(container)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (draggable)
        self.header = QFrame()
        self.header.setFixedHeight(50)
        self.header.setStyleSheet("QFrame { background: white; border: none; border-bottom: 1px solid #e0e0e0; }")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("📋 Clipboard")
        title.setFont(QFont("Ubuntu", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #1f1f1f; border: none;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings button (replaces pin - simpler)
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #f3f3f3;
            }
        """)
        self.settings_btn.clicked.connect(self.toggle_settings)
        header_layout.addWidget(self.settings_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                color: #707070;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #ffebee;
                color: #d32f2f;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(self.header)
        
        # Search box
        search_container = QFrame()
        search_container.setStyleSheet("QFrame { background: white; border: none; }")
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(15, 10, 15, 10)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search clipboard...")
        self.search_box.setFont(QFont("Ubuntu", 10))
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #f5f5f5;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                color: #1f1f1f;
            }
            QLineEdit::placeholder {
                color: #707070;
            }
        """)
        self.search_box.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_box)
        
        layout.addWidget(search_container)
        
        # Scrollable content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: white; border: none; }")
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(15, 5, 15, 5)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # Footer
        footer = QFrame()
        footer.setFixedHeight(35)
        footer.setStyleSheet("QFrame { background: white; border: none; border-top: 1px solid #e0e0e0; }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 0, 15, 0)
        
        count = len(self.manager.clip_history)
        info = QLabel(f"{count} items • ↑↓ Enter Esc Del")
        info.setFont(QFont("Ubuntu", 8))
        info.setStyleSheet("color: #707070; border: none;")
        footer_layout.addWidget(info)
        
        layout.addWidget(footer)
        
        # Populate items
        self.item_widgets = []
        self.populate_items()
        
        # Set size
        self.setFixedSize(450, 550)
        
    def populate_items(self):
        # Clear existing
        for widget in self.item_widgets:
            widget.deleteLater()
        self.item_widgets.clear()
        
        history = list(reversed(list(self.manager.clip_history)))
        
        if not history:
            empty = QLabel("No clipboard history yet")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFont(QFont("Ubuntu", 10))
            empty.setStyleSheet("color: #707070; padding: 50px;")
            self.scroll_layout.insertWidget(0, empty)
            self.item_widgets.append(empty)
            return
            
        for i, text in enumerate(history):
            item = ClipboardItem(text, i)
            item.clicked.connect(self.paste_item)
            self.scroll_layout.insertWidget(i, item)
            self.item_widgets.append(item)
            
        if self.item_widgets:
            self.select_item(0)
            
    def filter_items(self, query):
        query = query.lower()
        history = list(reversed(list(self.manager.clip_history)))
        
        for i, widget in enumerate(self.item_widgets):
            if isinstance(widget, ClipboardItem):
                if not query or query in history[i].lower():
                    widget.show()
                else:
                    widget.hide()
                    
    def select_item(self, index):
        visible_items = [w for w in self.item_widgets if isinstance(w, ClipboardItem) and w.isVisible()]
        if not visible_items or index < 0 or index >= len(visible_items):
            return
            
        for item in visible_items:
            item.set_selected(False)
            
        visible_items[index].set_selected(True)
        self.selected_index = index
        
        # Auto-scroll to selected
        self.scroll_area.ensureWidgetVisible(visible_items[index])
        
    def paste_item(self, index):
        history = list(self.manager.clip_history)
        actual_idx = len(history) - 1 - index
        text = history[actual_idx]
        
        self.close()
        QTimer.singleShot(50, lambda: self.manager.paste_text(text))
        
    def toggle_settings(self):
        """Show/hide auto-paste toggle"""
        self.manager.auto_paste = not self.manager.auto_paste
        self.manager.save_config()
        status = "ON" if self.manager.auto_paste else "OFF"
        print(f"Auto-paste: {status}")
        
    def position_near_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        
        x = max(0, min(cursor_pos.x() - self.width() // 2, screen.width() - self.width()))
        y = max(0, min(cursor_pos.y() + 20, screen.height() - self.height()))
        
        self.move(x, y)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.header.geometry().contains(event.pos()):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            
    def keyPressEvent(self, event):
        visible = [w for w in self.item_widgets if isinstance(w, ClipboardItem) and w.isVisible()]
        
        if event.key() == Qt.Key.Key_Down and visible:
            self.select_item(min(self.selected_index + 1, len(visible) - 1))
        elif event.key() == Qt.Key.Key_Up and visible:
            self.select_item(max(self.selected_index - 1, 0))
        elif event.key() == Qt.Key.Key_Return and visible:
            self.paste_item(visible[self.selected_index].index)
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Delete and visible:
            idx = visible[self.selected_index].index
            history = list(self.manager.clip_history)
            actual_idx = len(history) - 1 - idx
            self.manager.clip_history.remove(history[actual_idx])
            self.manager.save_config()
            self.close()
            QTimer.singleShot(50, self.manager.show_ui)


class ClipboardManager:
    def __init__(self):
        self.max_size = 100
        self.auto_paste = True
        self.clip_history = deque(maxlen=self.max_size)
        self.last_saved = ""
        self.running = True
        self.keyboard_controller = Controller()
        self.ui_window = None
        
        self.load_config()
        
        # Clipboard monitor
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_clipboard)
        self.timer.start(300)
        
        # Initial clipboard
        try:
            self.last_saved = pc.paste()
        except:
            self.last_saved = ""
            
        # Global hotkeys
        self.needs_show_ui = False
        self.needs_paste_latest = False
        
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
            print("🚀 Clipboard Manager Started (Qt6)")
            print("   Ctrl+Alt+V - Show history")
            print("   Ctrl+Shift+V - Paste latest")
        except Exception as e:
            print(f"⚠️ Hotkey error: {e}")
            
        # Check for hotkey requests
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.check_hotkeys)
        self.hotkey_timer.start(50)
        
    def check_hotkeys(self):
        if self.needs_show_ui:
            self.needs_show_ui = False
            self.show_ui()
        if self.needs_paste_latest:
            self.needs_paste_latest = False
            self.paste_latest()
            
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
            
    def check_clipboard(self):
        try:
            current = pc.paste()
            if current and current != self.last_saved:
                if current not in self.clip_history:
                    self.clip_history.append(current)
                    self.save_config()
                self.last_saved = current
        except:
            pass
            
    def paste_text(self, text):
        pc.copy(text)
        QTimer.singleShot(50, self._do_paste)
        
    def _do_paste(self):
        try:
            self.keyboard_controller.press(Key.ctrl_l)
            QTimer.singleShot(20, lambda: self.keyboard_controller.press('v'))
            QTimer.singleShot(40, lambda: self.keyboard_controller.release('v'))
            QTimer.singleShot(60, lambda: self.keyboard_controller.release(Key.ctrl_l))
        except:
            pass
            
    def paste_latest(self):
        if self.clip_history:
            latest = list(self.clip_history)[-1]
            self.paste_text(latest)
            
    def show_ui(self):
        if self.ui_window is None or not self.ui_window.isVisible():
            self.ui_window = ClipboardUI(self)
            self.ui_window.show()
            self.ui_window.activateWindow()
            self.ui_window.raise_()
            
    def stop(self):
        self.running = False
        self.timer.stop()
        self.hotkey_timer.stop()
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
        self.save_config()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    manager = ClipboardManager()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n👋 Stopped")
        manager.stop()
        sys.exit(0)