ACCENT = '#8B0000'
ACCENT_LIGHT = '#c0392b'
BG = '#141414'
BG2 = '#1c1c1c'
BG3 = '#242424'
BORDER = '#2e2e2e'
TEXT = '#e0e0e0'
DIM = '#777777'
SUCCESS = '#2e7d32'
WARNING = '#f57f17'

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

/* ── Sidebar ── */
#sidebar {{
    background-color: {BG2};
    border-right: 1px solid {BORDER};
    min-width: 200px;
    max-width: 220px;
}}

#sidebar-title {{
    color: {ACCENT_LIGHT};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.15em;
    padding: 14px 12px 6px 12px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: none;
    background-color: {BG};
}}

QTabBar {{
    background: {BG2};
}}

QTabBar::tab {{
    background: {BG2};
    color: {DIM};
    padding: 9px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    letter-spacing: 0.08em;
}}

QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT_LIGHT};
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT};
    background: {BG3};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 7px 16px;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: #2e2e2e;
    border-color: #444;
}}

QPushButton:pressed {{
    background-color: #1a1a1a;
}}

QPushButton:disabled {{
    color: #444;
    border-color: #222;
}}

QPushButton#btn-primary {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #fff;
    font-weight: bold;
    letter-spacing: 0.06em;
    padding: 9px 24px;
}}

QPushButton#btn-primary:hover {{
    background-color: {ACCENT_LIGHT};
    border-color: {ACCENT_LIGHT};
}}

QPushButton#btn-primary:disabled {{
    background-color: #3a1010;
    border-color: #3a1010;
    color: #666;
}}

QPushButton#btn-stop {{
    background-color: #1a1a1a;
    border-color: {ACCENT};
    color: {ACCENT_LIGHT};
}}

QPushButton#btn-stop:hover {{
    background-color: {ACCENT};
    color: #fff;
}}

QPushButton#btn-icon {{
    background-color: {BG3};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 15px;
    min-width: 44px;
    max-width: 60px;
}}

QPushButton#btn-icon:hover {{
    background-color: #2e2e2e;
    border-color: {ACCENT};
}}

/* ── Device list ── */
QListWidget {{
    background: {BG2};
    border: none;
    outline: none;
    padding: 4px 0;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {BG};
    color: {DIM};
}}

QListWidget::item:selected {{
    background: {BG3};
    color: {TEXT};
    border-left: 2px solid {ACCENT_LIGHT};
}}

QListWidget::item:hover:!selected {{
    background: #1e1e1e;
    color: {TEXT};
}}

/* ── Inputs ── */
QLineEdit, QSpinBox, QComboBox {{
    background: {BG3};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 6px 10px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {BG3};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    outline: none;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {DIM};
    width: 0;
    height: 0;
    margin-right: 6px;
}}

/* ── CheckBox ── */
QCheckBox {{
    spacing: 8px;
    color: {TEXT};
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER};
    border-radius: 2px;
    background: {BG3};
}}

QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Labels ── */
QLabel#section-title {{
    color: {ACCENT_LIGHT};
    font-size: 10px;
    letter-spacing: 0.18em;
    font-weight: bold;
    padding: 4px 0 2px 0;
}}

QLabel#status-ok {{
    color: #4caf50;
    font-size: 12px;
}}

QLabel#status-err {{
    color: {ACCENT_LIGHT};
    font-size: 12px;
}}

QLabel#status-dim {{
    color: {DIM};
    font-size: 12px;
}}

QLabel#url-label {{
    background: {BG3};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 7px 10px;
    color: #4fc3f7;
    font-size: 13px;
}}

/* ── Table / file list ── */
QTableWidget {{
    background: {BG2};
    border: none;
    gridline-color: {BORDER};
    outline: none;
}}

QTableWidget::item {{
    padding: 5px 8px;
    border-bottom: 1px solid {BORDER};
}}

QTableWidget::item:selected {{
    background: {BG3};
    color: {TEXT};
}}

QHeaderView::section {{
    background: {BG3};
    color: {DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-size: 11px;
    letter-spacing: 0.08em;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {BG2};
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: #333;
    border-radius: 3px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: #555;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
    max-height: 1px;
}}

/* ── Status bar ── */
QStatusBar {{
    background: {BG2};
    color: {DIM};
    font-size: 11px;
    border-top: 1px solid {BORDER};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    color: {DIM};
    font-size: 11px;
    letter-spacing: 0.1em;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {DIM};
}}

/* ── ToolTip ── */
QToolTip {{
    background: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 12px;
}}
"""
