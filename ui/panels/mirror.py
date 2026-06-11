import os
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGridLayout, QLineEdit, QFrame,
    QScrollArea, QSizePolicy,
)

from core.adb import ADB
from core.scrcpy import ScrcpyManager, ScrcpyConfig

KEYCODES = {
    '⌂ Home':     'KEYCODE_HOME',
    '← Back':     'KEYCODE_BACK',
    '□ Recent':   'KEYCODE_APP_SWITCH',
    '▲ Vol+':     'KEYCODE_VOLUME_UP',
    '▼ Vol−':     'KEYCODE_VOLUME_DOWN',
    '⏻ Power':    'KEYCODE_POWER',
    '📷 Shot':    'KEYCODE_SYSRQ',
    '🔒 Lock':    'KEYCODE_SLEEP',
}


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section-title')
    return lbl


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    return line


class MirrorPanel(QWidget):
    def __init__(self, adb: ADB, scrcpy: ScrcpyManager, settings: QSettings):
        super().__init__()
        self.adb = adb
        self.scrcpy = scrcpy
        self.settings = settings
        self._serial = ''
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._check_process)
        self._build_ui()

    def set_device(self, serial: str):
        self._serial = serial
        enabled = bool(serial)
        self.launch_btn.setEnabled(enabled and not self.scrcpy.is_running())
        self.stop_btn.setEnabled(self.scrcpy.is_running())
        for btn in self._ctrl_buttons:
            btn.setEnabled(enabled)
        self.clip_push_btn.setEnabled(enabled)

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Mirror Settings ─────────────────────────────────
        layout.addWidget(_section('Mirror Settings'))

        opts = QGridLayout()
        opts.setHorizontalSpacing(16)
        opts.setVerticalSpacing(8)

        opts.addWidget(QLabel('Max Size'), 0, 0)
        self.size_combo = QComboBox()
        for s in ('480', '720', '1080', '1440', '2160'):
            self.size_combo.addItem(s + 'p', s)
        self.size_combo.setCurrentIndex(2)
        opts.addWidget(self.size_combo, 0, 1)

        opts.addWidget(QLabel('Bitrate'), 0, 2)
        self.bitrate_combo = QComboBox()
        for b in ('2M', '4M', '8M', '16M'):
            self.bitrate_combo.addItem(b, b)
        self.bitrate_combo.setCurrentIndex(2)
        opts.addWidget(self.bitrate_combo, 0, 3)

        opts.addWidget(QLabel('Max FPS'), 1, 0)
        self.fps_combo = QComboBox()
        for f in ('24', '30', '60'):
            self.fps_combo.addItem(f + ' fps', f)
        self.fps_combo.setCurrentIndex(2)
        opts.addWidget(self.fps_combo, 1, 1)

        layout.addLayout(opts)

        flags = QHBoxLayout()
        flags.setSpacing(20)
        self.cb_screen_off = QCheckBox('Turn screen off')
        self.cb_touches = QCheckBox('Show touches')
        self.cb_stay_awake = QCheckBox('Stay awake')
        self.cb_stay_awake.setChecked(True)
        self.cb_on_top = QCheckBox('Always on top')
        for cb in (self.cb_screen_off, self.cb_touches, self.cb_stay_awake, self.cb_on_top):
            flags.addWidget(cb)
        flags.addStretch()
        layout.addLayout(flags)

        btn_row = QHBoxLayout()
        self.launch_btn = QPushButton('▶  LAUNCH MIRROR')
        self.launch_btn.setObjectName('btn-primary')
        self.launch_btn.setEnabled(False)
        self.launch_btn.clicked.connect(self._launch)

        self.stop_btn = QPushButton('■  STOP')
        self.stop_btn.setObjectName('btn-stop')
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

        btn_row.addWidget(self.launch_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.mirror_status = QLabel('')
        self.mirror_status.setObjectName('status-dim')
        layout.addWidget(self.mirror_status)

        layout.addWidget(_hline())

        # ── Quick Controls ───────────────────────────────────
        layout.addWidget(_section('Quick Controls'))

        ctrl_grid = QGridLayout()
        ctrl_grid.setSpacing(6)
        self._ctrl_buttons = []
        for i, (label, keycode) in enumerate(KEYCODES.items()):
            btn = QPushButton(label)
            btn.setObjectName('btn-icon')
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, kc=keycode: self._send_key(kc))
            ctrl_grid.addWidget(btn, i // 4, i % 4)
            self._ctrl_buttons.append(btn)

        screenshot_btn = QPushButton('📸  Screenshot')
        screenshot_btn.clicked.connect(self._screenshot)
        screenshot_btn.setEnabled(False)
        ctrl_grid.addWidget(screenshot_btn, 2, 0, 1, 2)
        self._ctrl_buttons.append(screenshot_btn)

        layout.addLayout(ctrl_grid)
        layout.addWidget(_hline())

        # ── Clipboard ────────────────────────────────────────
        layout.addWidget(_section('Clipboard'))

        clip_row = QHBoxLayout()
        self.clip_input = QLineEdit()
        self.clip_input.setPlaceholderText('Type text to push to phone…')
        self.clip_push_btn = QPushButton('→ Push to Phone')
        self.clip_push_btn.setEnabled(False)
        self.clip_push_btn.clicked.connect(self._push_clipboard)
        clip_row.addWidget(self.clip_input, 1)
        clip_row.addWidget(self.clip_push_btn)
        layout.addLayout(clip_row)

        note = QLabel('Phone → PC clipboard requires the Clipper app installed on the device.')
        note.setObjectName('status-dim')
        layout.addWidget(note)

        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _build_config(self) -> ScrcpyConfig:
        return ScrcpyConfig(
            max_size=int(self.size_combo.currentData()),
            bit_rate=self.bitrate_combo.currentData(),
            max_fps=int(self.fps_combo.currentData()),
            turn_screen_off=self.cb_screen_off.isChecked(),
            show_touches=self.cb_touches.isChecked(),
            stay_awake=self.cb_stay_awake.isChecked(),
            always_on_top=self.cb_on_top.isChecked(),
        )

    def _launch(self):
        if not self._serial:
            return
        ok, err = self.scrcpy.launch(self._serial, self._build_config())
        if ok:
            self.launch_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.mirror_status.setText('scrcpy running…')
            self.mirror_status.setObjectName('status-ok')
            self._poll_timer.start()
        else:
            self.mirror_status.setText(f'Failed: {err}')
            self.mirror_status.setObjectName('status-err')
        self.mirror_status.setStyleSheet('')

    def _stop(self):
        self.scrcpy.stop()
        self._poll_timer.stop()
        self.launch_btn.setEnabled(bool(self._serial))
        self.stop_btn.setEnabled(False)
        self.mirror_status.setText('')

    def _check_process(self):
        if self.scrcpy.poll() is not None:
            self._poll_timer.stop()
            self.launch_btn.setEnabled(bool(self._serial))
            self.stop_btn.setEnabled(False)
            self.mirror_status.setText('scrcpy exited')
            self.mirror_status.setObjectName('status-dim')
            self.mirror_status.setStyleSheet('')

    def _send_key(self, keycode: str):
        if self._serial:
            self.adb.keyevent(self._serial, keycode)

    def _screenshot(self):
        if not self._serial:
            return
        folder = os.path.expanduser('~/Desktop')
        ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        path = os.path.join(folder, f'droidcast_{ts}.png')
        ok = self.adb.screenshot(self._serial, path)
        if ok:
            self.mirror_status.setText(f'Screenshot saved → {path}')
            self.mirror_status.setObjectName('status-ok')
        else:
            self.mirror_status.setText('Screenshot failed')
            self.mirror_status.setObjectName('status-err')
        self.mirror_status.setStyleSheet('')

    def _push_clipboard(self):
        if not self._serial:
            return
        text = self.clip_input.text()
        if text:
            self.adb.push_clipboard(self._serial, text)
            self.mirror_status.setText('Clipboard pushed to phone')
            self.mirror_status.setObjectName('status-ok')
            self.mirror_status.setStyleSheet('')
