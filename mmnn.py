#!/usr/bin/env python3
"""
Clipboard Manager for Linux (Windows 11 Style) - Qt6 Version
Compact, smooth, and feature-rich like Windows 11
"""

import sys
import json
import os
from collections import deque
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QLineEdit, QScrollArea, 
                              QFrame, QPushButton, QDialog, QCheckBox, QSpinBox,
                              QComboBox)
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QCursor, QPainter, QLinearGradient, QColor, QPalette
import pyperclip as pc
from pynput import keyboard as pynput_kb
from pynput.keyboard import Controller, Key

CONFIG_FILE = os.path.expanduser("~/.clipboard_manager_config.json")

# Modern color themes
THEMES = {
    'light': {
        'bg': '#ffffff',
        'bg_secondary': '#f8f9fa',
        'hover': '#e9ecef',
        'select': '#0078d4',
        'select_text': '#ffffff',
        'border': '#dee2e6',
        'text': '#212529',
        'text_secondary': '#6c757d',
        'shadow': 'rgba(0,0,0,0.1)'
    },
    'dark': {
        'bg': '#202020',
        'bg_secondary': '#2d2d2d',
        'hover': '#383838',
        'select': '#0078d4',
        'select_text': '#ffffff',
        'border': '#404040',
        'text': '#ffffff',
        'text_secondary': '#b0b0b0',
        'shadow': 'rgba(0,0,0,0.3)'
    },
    'auto': {  # System adaptive
        'bg': '#ffffff',
        'bg_secondary': '#f8f9fa',
        'hover': '#e9ecef',
        'select': '#0078d4',
        'select_text': '#ffffff',
        'border': '#dee2e6',
        'text': '#212529',
        'text_secondary': '#6c757d',
        'shadow': 'rgba(0,0,0,0.1)'
    }
}


class SettingsDialog(QDialog):
    """Settings panel"""
    
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Settings")
        self.setFixedSize(320, 380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Auto-paste
        self.auto_paste_cb = QCheckBox("Auto-paste on selection")
        self.auto_paste_cb.setChecked(manager.auto_paste)
        self.auto_paste_cb.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.auto_paste_cb)
        
        hint = QLabel("When enabled, clicking an item automatically pastes it")
        hint.setFont(QFont("Segoe UI", 8))
        hint.setStyleSheet("color: #6c757d;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        # History size
        size_label = QLabel("History size:")
        size_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(size_label)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 500)
        self.size_spin.setValue(manager.max_size)
        self.size_spin.setSuffix(" items")
        self.size_spin.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.size_spin)
        
        # Theme
        theme_label = QLabel("Theme:")
        theme_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Auto (System)"])
        current_theme = manager.theme.capitalize()
        if current_theme == "Auto":
            current_theme = "Auto (System)"
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.theme_combo)
        
        # Window opacity
        opacity_label = QLabel(f"Window opacity: {int(manager.opacity * 100)}%")
        opacity_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.opacity_label = opacity_label
        layout.addWidget(opacity_label)
        
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(70, 100)
        self.opacity_spin.setValue(int(manager.opacity * 100))
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.setFont(QFont("Segoe UI", 10))
        self.opacity_spin.valueChanged.connect(lambda v: opacity_label.setText(f"Window opacity: {v}%"))
        layout.addWidget(self.opacity_spin)
        
        # Compact mode
        self.compact_cb = QCheckBox("Compact mode (smaller items)")
        self.compact_cb.setChecked(manager.compact_mode)
        self.compact_cb.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.compact_cb)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear History")
        clear_btn.setFont(QFont("Segoe UI", 9))
        clear_btn.clicked.connect(self.clear_history)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background: #006abc;
            }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        self.apply_theme()
        
    def apply_theme(self):
        theme = THEMES[self.manager.theme]
        self.setStyleSheet(f"""
            QDialog {{
                background: {theme['bg']};
                color: {theme['text']};
            }}
            QLabel {{
                color: {theme['text']};
            }}
            QCheckBox {{
                color: {theme['text']};
            }}
            QSpinBox, QComboBox {{
                background: {theme['bg_secondary']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 6px;
                color: {theme['text']};
            }}
        """)
        
    def clear_history(self):
        self.manager.clip_history.clear()
        self.manager.save_config()
        self.accept()
        
    def save_settings(self):
        self.manager.auto_paste = self.auto_paste_cb.isChecked()
        self.manager.max_size = self.size_spin.value()
        self.manager.opacity = self.opacity_spin.value() / 100
        self.manager.compact_mode = self.compact_cb.isChecked()
        
        theme_map = {"Light": "light", "Dark": "dark", "Auto (System)": "auto"}
        self.manager.theme = theme_map[self.theme_combo.currentText()]
        
        self.manager.clip_history = deque(list(self.manager.clip_history), maxlen=self.manager.max_size)
        self.manager.save_config()
        self.accept()


class ClipboardItem(QFrame):
    """Compact clipboard item with text truncation and fade effect"""
    clicked = pyqtSignal(int)
    
    def __init__(self, text, index, theme, compact=False, parent=None):
        super().__init__(parent)
        self.index = index
        self.text = text
        self.is_selected = False
        self.theme = theme
        self.compact = compact
        
        height = 48 if compact else 60
        self.setFixedHeight(height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        margins = (10, 6, 10, 6) if compact else (12, 8, 12, 8)
        layout.setContentsMargins(*margins)
        layout.setSpacing(2 if compact else 4)
        
        # Preview text (truncated, no horizontal scroll)
        preview = text.replace('\n', ' ').replace('\t', ' ').strip()
        max_len = 60 if compact else 70
        if len(preview) > max_len:
            preview = preview[:max_len] + '...'
            
        self.text_label = QLabel(preview)
        font_size = 9 if compact else 10
        self.text_label.setFont(QFont("Segoe UI", font_size))
        self.text_label.setWordWrap(False)
        layout.addWidget(self.text_label)
        
        # Type indicator (compact)
        if text.startswith(('http://', 'https://')):
            typ = "🔗 Link"
        elif text.replace('.','').replace('-','').isdigit():
            typ = "🔢 Number"
        elif '\n' in text:
            words = len(text.split())
            typ = f"📄 {words} word" + ("s" if words != 1 else "")
        else:
            typ = "📝 Text"
            
        self.type_label = QLabel(typ)
        type_size = 7 if compact else 8
        self.type_label.setFont(QFont("Segoe UI", type_size))
        layout.addWidget(self.type_label)
        
        self.update_style()
        
    def update_style(self):
        if self.is_selected:
            bg = self.theme['select']
            text_color = self.theme['select_text']
        else:
            bg = self.theme['bg']
            text_color = self.theme['text']
            
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border-radius: 4px;
                border: none;
            }}
        """)
        self.text_label.setStyleSheet(f"color: {text_color};")
        self.type_label.setStyleSheet(f"color: {self.theme['select_text'] if self.is_selected else self.theme['text_secondary']};")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
            
    def enterEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {self.theme['hover']};
                    border-radius: 4px;
                }}
            """)
            
    def leaveEvent(self, event):
        if not self.is_selected:
            self.update_style()
            
    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()


class FadeOverlay(QWidget):
    """Gradient fade overlay for bottom of scroll area"""
    
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        base_color = QColor(self.theme['bg'])
        gradient.setColorAt(0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.3, QColor(base_color.red(), base_color.green(), base_color.blue(), 50))
        gradient.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 255))
        
        painter.fillRect(self.rect(), gradient)


class ClipboardUI(QMainWindow):
    """Compact, modern clipboard UI"""
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.selected_index = 0
        self.drag_position = QPoint()
        self.theme = THEMES[manager.theme]
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(manager.opacity)
        
        self.setup_ui()
        self.position_near_cursor()
        
        # Fade in animation
        self.fade_in()
        
    def fade_in(self):
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.manager.opacity)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
        
    def setup_ui(self):
        # Main container
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background: {self.theme['bg']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
            }}
        """)
        self.setCentralWidget(container)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Compact header
        self.header = QFrame()
        self.header.setFixedHeight(42)
        self.header.setStyleSheet(f"""
            QFrame {{ 
                background: {self.theme['bg']}; 
                border: none; 
                border-bottom: 1px solid {self.theme['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        
        title = QLabel("📋 Clipboard")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.theme['text']}; border: none;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings icon
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 14px;
                color: {self.theme['text_secondary']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {self.theme['hover']};
            }}
        """)
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 13px;
                color: {self.theme['text_secondary']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: #e81123;
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(self.header)
        
        # Compact search
        search_container = QFrame()
        search_container.setStyleSheet(f"QFrame {{ background: {self.theme['bg']}; border: none; }}")
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(10, 8, 10, 8)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search...")
        self.search_box.setFont(QFont("Segoe UI", 9))
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background: {self.theme['bg_secondary']};
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                padding: 6px 10px;
                color: {self.theme['text']};
            }}
            QLineEdit::placeholder {{
                color: {self.theme['text_secondary']};
            }}
        """)
        self.search_box.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_box)
        
        layout.addWidget(search_container)
        
        # Scroll area with fade effect
        scroll_container = QWidget()
        scroll_container.setStyleSheet(f"background: {self.theme['bg']};")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        scroll_container_layout.setSpacing(0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ 
                background: {self.theme['bg']}; 
                border: none; 
            }}
            QScrollBar:vertical {{
                background: {self.theme['bg']};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.theme['text_secondary']};
            }}
        """)
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(10, 4, 10, 4)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        scroll_container_layout.addWidget(self.scroll_area)
        
        # Add fade overlay
        self.fade_overlay = FadeOverlay(self.theme)
        self.fade_overlay.setFixedHeight(40)
        scroll_container_layout.addWidget(self.fade_overlay)
        scroll_container_layout.setStretch(0, 1)
        
        layout.addWidget(scroll_container)
        
        # Compact footer
        footer = QFrame()
        footer.setFixedHeight(28)
        footer.setStyleSheet(f"""
            QFrame {{ 
                background: {self.theme['bg']}; 
                border: none; 
                border-top: 1px solid {self.theme['border']};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)
        
        count = len(self.manager.clip_history)
        info = QLabel(f"{count} items")
        info.setFont(QFont("Segoe UI", 8))
        info.setStyleSheet(f"color: {self.theme['text_secondary']}; border: none;")
        footer_layout.addWidget(info)
        
        footer_layout.addStretch()
        
        shortcuts = QLabel("↑↓ Enter Esc Del")
        shortcuts.setFont(QFont("Segoe UI", 7))
        shortcuts.setStyleSheet(f"color: {self.theme['text_secondary']}; border: none;")
        footer_layout.addWidget(shortcuts)
        
        layout.addWidget(footer)
        
        # Populate items
        self.item_widgets = []
        self.populate_items()
        
        # Compact size
        self.setFixedSize(340, 480)
        
    def populate_items(self):
        for widget in self.item_widgets:
            widget.deleteLater()
        self.item_widgets.clear()
        
        history = list(reversed(list(self.manager.clip_history)))
        
        if not history:
            empty = QLabel("No clipboard history")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFont(QFont("Segoe UI", 9))
            empty.setStyleSheet(f"color: {self.theme['text_secondary']}; padding: 40px;")
            self.scroll_layout.insertWidget(0, empty)
            self.item_widgets.append(empty)
            return
            
        for i, text in enumerate(history):
            item = ClipboardItem(text, i, self.theme, self.manager.compact_mode)
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
        self.scroll_area.ensureWidgetVisible(visible_items[index])
        
    def paste_item(self, index):
        history = list(self.manager.clip_history)
        actual_idx = len(history) - 1 - index
        text = history[actual_idx]
        
        self.close()
        
        if self.manager.auto_paste:
            QTimer.singleShot(50, lambda: self.manager.paste_text(text))
        else:
            pc.copy(text)
        
    def open_settings(self):
        dialog = SettingsDialog(self.manager, self)
        if dialog.exec():
            self.close()
            QTimer.singleShot(100, self.manager.show_ui)
        
    def position_near_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        
        x = max(10, min(cursor_pos.x() - self.width() // 2, screen.width() - self.width() - 10))
        y = max(10, min(cursor_pos.y() + 20, screen.height() - self.height() - 10))
        
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
        self.theme = 'light'
        self.opacity = 0.97
        self.compact_mode = False
        self.clip_history = deque(maxlen=self.max_size)
        self.last_saved = ""
        self.running = True
        self.keyboard_controller = Controller()
        self.ui_window = None
        
        self.load_config()
        
        # Detect system theme
        if self.theme == 'auto':
            self.detect_system_theme()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_clipboard)
        self.timer.start(300)
        
        try:
            self.last_saved = pc.paste()
        except:
            self.last_saved = ""
            
        self.needs_show_ui = False
        self.needs_paste_latest = False
        
        def _request_show_ui():
            self.needs_show_ui = True
            
        def _request_paste_latest():
            self.needs_paste_latest = True
            
        try:
            self.hotkey_listener = pynput_kb.GlobalHotKeys({
                # '<ctrl>+<alt>+v': _request_show_ui,
                '<cmd>+v': _request_show_ui,
                # '<ctrl>+<shift>+v': _request_paste_latest,
            })
            self.hotkey_listener.start()
            print("🚀 Clipboard Manager Ready")
            print("   Ctrl+Alt+V - Show clipboard")
            print("   Ctrl+Shift+V - Paste latest")
        except Exception as e:
            print(f"⚠️ Hotkey error: {e}")
            
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.check_hotkeys)
        self.hotkey_timer.start(50)
        
    def detect_system_theme(self):
        # Simple detection based on palette
        palette = QApplication.palette()
        bg = palette.color(QPalette.ColorRole.Window)
        if bg.lightness() < 128:
            THEMES['auto'] = THEMES['dark'].copy()
        else:
            THEMES['auto'] = THEMES['light'].copy()
        
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
                    self.theme = config.get('theme', 'light')
                    self.opacity = config.get('opacity', 0.97)
                    self.compact_mode = config.get('compact_mode', False)
                    self.clip_history = deque(config.get('history', []), maxlen=self.max_size)
        except Exception as e:
            print(f"⚠️ Config load error: {e}")
            
    def save_config(self):
        try:
            config = {
                'max_size': self.max_size,
                'auto_paste': self.auto_paste,
                'theme': self.theme,
                'opacity': self.opacity,
                'compact_mode': self.compact_mode,
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
        else:
            self.ui_window.close()
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