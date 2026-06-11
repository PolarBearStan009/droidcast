import os
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QScrollArea, QFileDialog,
    QListWidget, QListWidgetItem,
)

from core.scrcpy import ScrcpyManager, ScrcpyConfig
from utils.platform import open_path


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section-title')
    return lbl


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    return line


class RecordPanel(QWidget):
    def __init__(self, scrcpy: ScrcpyManager, settings: QSettings):
        super().__init__()
        self.scrcpy = scrcpy
        self.settings = settings
        self._serial = ''
        self._recording = False
        self._elapsed = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._build_ui()
        self._load_recordings()

    def set_device(self, serial: str):
        self._serial = serial
        self.record_btn.setEnabled(bool(serial) and not self._recording)

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        layout.addWidget(_section('Recording'))

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel('Output folder'))
        default_folder = os.path.expanduser('~/Movies/Droidcast')
        self.folder_input = QLineEdit(self.settings.value('record_folder', default_folder))
        self.folder_input.textChanged.connect(lambda t: self.settings.setValue('record_folder', t))
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel('Max Size'))
        self.size_combo = QComboBox()
        for s in ('480', '720', '1080', '1440'):
            self.size_combo.addItem(s + 'p', s)
        self.size_combo.setCurrentIndex(2)
        quality_row.addWidget(self.size_combo)

        quality_row.addWidget(QLabel('Bitrate'))
        self.bitrate_combo = QComboBox()
        for b in ('4M', '8M', '16M'):
            self.bitrate_combo.addItem(b, b)
        self.bitrate_combo.setCurrentIndex(1)
        quality_row.addWidget(self.bitrate_combo)
        quality_row.addStretch()
        layout.addLayout(quality_row)

        btn_row = QHBoxLayout()
        self.record_btn = QPushButton('⏺  START RECORDING')
        self.record_btn.setObjectName('btn-primary')
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self._toggle)

        self.timer_label = QLabel('00:00')
        self.timer_label.setObjectName('status-dim')
        self.timer_label.setVisible(False)

        btn_row.addWidget(self.record_btn)
        btn_row.addWidget(self.timer_label)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.rec_status = QLabel('')
        self.rec_status.setObjectName('status-dim')
        layout.addWidget(self.rec_status)

        layout.addWidget(_hline())

        layout.addWidget(_section('Recent Recordings'))

        self.rec_list = QListWidget()
        self.rec_list.setMaximumHeight(200)
        layout.addWidget(self.rec_list)

        rec_btns = QHBoxLayout()
        open_btn = QPushButton('▶  Open')
        folder_btn = QPushButton('📁  Show in Folder')
        open_btn.clicked.connect(self._open_recording)
        folder_btn.clicked.connect(self._open_folder)
        rec_btns.addWidget(open_btn)
        rec_btns.addWidget(folder_btn)
        rec_btns.addStretch()
        layout.addLayout(rec_btns)

        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose output folder',
                                                   self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def _toggle(self):
        if self._recording:
            self._stop()
        else:
            self._start()

    def _start(self):
        if not self._serial:
            return
        folder = self.folder_input.text()
        record_path = ScrcpyManager.make_record_path(folder)

        config = ScrcpyConfig(
            max_size=int(self.size_combo.currentData()),
            bit_rate=self.bitrate_combo.currentData(),
            record_path=record_path,
        )
        ok, err = self.scrcpy.launch(self._serial, config)
        if not ok:
            self.rec_status.setText(f'Failed: {err}')
            self.rec_status.setObjectName('status-err')
            self.rec_status.setStyleSheet('')
            return

        self._recording = True
        self._elapsed = 0
        self._timer.start()
        self.record_btn.setText('⏹  STOP RECORDING')
        self.timer_label.setVisible(True)
        self.rec_status.setText(f'Saving to: {record_path}')
        self.rec_status.setObjectName('status-ok')
        self.rec_status.setStyleSheet('')

    def _stop(self):
        self.scrcpy.stop()
        self._recording = False
        self._timer.stop()
        self.record_btn.setText('⏺  START RECORDING')
        self.record_btn.setEnabled(bool(self._serial))
        self.timer_label.setVisible(False)
        self.rec_status.setText('Recording saved.')
        self.rec_status.setStyleSheet('')
        self._load_recordings()

    def _tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f'{m:02d}:{s:02d}')
        if self.scrcpy.poll() is not None:
            self._stop()

    def _load_recordings(self):
        self.rec_list.clear()
        folder = self.folder_input.text()
        if not os.path.isdir(folder):
            return
        files = sorted(
            [f for f in os.listdir(folder) if f.endswith('.mp4')],
            reverse=True,
        )
        for f in files[:20]:
            path = os.path.join(folder, f)
            size_mb = os.path.getsize(path) / 1_048_576
            item = QListWidgetItem(f'  {f}  ({size_mb:.1f} MB)')
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.rec_list.addItem(item)

    def _open_recording(self):
        item = self.rec_list.currentItem()
        if not item:
            return
        open_path(item.data(Qt.ItemDataRole.UserRole))

    def _open_folder(self):
        folder = self.folder_input.text()
        if os.path.isdir(folder):
            open_path(folder)
