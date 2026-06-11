import os
import shutil
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFileDialog, QFrame, QScrollArea,
    QSpinBox,
)

from core.adb import ADB
from core.scrcpy import ScrcpyManager


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section-title')
    return lbl


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    return line


class SettingsPanel(QWidget):
    def __init__(self, settings: QSettings, adb: ADB, scrcpy: ScrcpyManager):
        super().__init__()
        self.settings = settings
        self.adb = adb
        self.scrcpy = scrcpy
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Tool paths ───────────────────────────────────────
        layout.addWidget(_section('Tool Paths'))

        self.adb_input = self._path_row(layout, 'adb', 'adb_path', 'adb')
        self.scrcpy_input = self._path_row(layout, 'scrcpy', 'scrcpy_path', 'scrcpy')
        self.ffmpeg_input = self._path_row(layout, 'ffmpeg', 'ffmpeg_path', 'ffmpeg')

        test_btn = QPushButton('Test All Tools')
        test_btn.clicked.connect(self._test_tools)
        layout.addWidget(test_btn)

        self.tool_status = QLabel('')
        self.tool_status.setObjectName('status-dim')
        self.tool_status.setWordWrap(True)
        layout.addWidget(self.tool_status)

        layout.addWidget(_hline())

        # ── Defaults ─────────────────────────────────────────
        layout.addWidget(_section('Defaults'))

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel('Record folder'))
        default_folder = os.path.expanduser('~/Movies/Droidcast')
        self.folder_input = QLineEdit(self.settings.value('record_folder', default_folder))
        self.folder_input.textChanged.connect(lambda t: self.settings.setValue('record_folder', t))
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel('Default stream port'))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(int(self.settings.value('stream_port', 8888)))
        self.port_spin.valueChanged.connect(lambda v: self.settings.setValue('stream_port', v))
        port_row.addWidget(self.port_spin)
        port_row.addStretch()
        layout.addLayout(port_row)

        layout.addWidget(_hline())

        # ── Behaviour ────────────────────────────────────────
        layout.addWidget(_section('Behaviour'))

        self.cb_tray = QCheckBox('Minimize to tray on close')
        self.cb_tray.setChecked(self.settings.value('minimize_to_tray', False, type=bool))
        self.cb_tray.toggled.connect(lambda v: self.settings.setValue('minimize_to_tray', v))
        layout.addWidget(self.cb_tray)

        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _path_row(self, parent_layout, label: str, key: str, default: str) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        detected = shutil.which(default) or ''
        inp = QLineEdit(self.settings.value(key, detected))
        inp.setPlaceholderText(f'auto-detect ({default})')
        inp.textChanged.connect(lambda t, k=key: self.settings.setValue(k, t))
        browse = QPushButton('Browse')
        browse.clicked.connect(lambda _, i=inp: self._browse_bin(i))
        row.addWidget(inp, 1)
        row.addWidget(browse)
        parent_layout.addLayout(row)
        return inp

    def _browse_bin(self, input_widget: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, 'Select executable')
        if path:
            input_widget.setText(path)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose folder', self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def _test_tools(self):
        results = []
        checks = [
            ('adb', self.adb_input.text() or 'adb'),
            ('scrcpy', self.scrcpy_input.text() or 'scrcpy'),
            ('ffmpeg', self.ffmpeg_input.text() or 'ffmpeg'),
        ]
        for name, path in checks:
            found = bool(shutil.which(path) or os.path.isfile(path))
            icon = '✓' if found else '✗'
            results.append(f'{icon} {name}: {path}')
        self.tool_status.setText('\n'.join(results))
        self.tool_status.setStyleSheet('')
