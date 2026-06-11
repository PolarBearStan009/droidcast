import shutil
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame, QScrollArea,
)

from core.adb import ADB
from core.streamer import Streamer
from utils.platform import open_url


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section-title')
    return lbl


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    return line


class StreamPanel(QWidget):
    def __init__(self, adb: ADB, streamer: Streamer, settings: QSettings):
        super().__init__()
        self.adb = adb
        self.streamer = streamer
        self.settings = settings
        self._serial = ''
        self._url = ''
        self._build_ui()

    def set_device(self, serial: str):
        self._serial = serial
        self.stream_btn.setEnabled(bool(serial) and not self.streamer.is_running())

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        layout.addWidget(_section('Stream Settings'))

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Resolution'))
        self.res_combo = QComboBox()
        for label, val in (('480×854', '480x854'), ('720×1280', '720x1280'),
                           ('1080×1920', '1080x1920')):
            self.res_combo.addItem(label, val)
        self.res_combo.setCurrentIndex(1)
        row1.addWidget(self.res_combo)

        row1.addWidget(QLabel('Bitrate'))
        self.bitrate_combo = QComboBox()
        for b in ('1M', '2M', '4M'):
            self.bitrate_combo.addItem(b, int(b[:-1]) * 1_000_000)
        self.bitrate_combo.setCurrentIndex(1)
        row1.addWidget(self.bitrate_combo)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Port'))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(int(self.settings.value('stream_port', 8888)))
        self.port_spin.valueChanged.connect(lambda v: self.settings.setValue('stream_port', v))
        row2.addWidget(self.port_spin)
        row2.addStretch()
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        self.stream_btn = QPushButton('▶  START STREAM')
        self.stream_btn.setObjectName('btn-primary')
        self.stream_btn.setEnabled(False)
        self.stream_btn.clicked.connect(self._toggle)
        btn_row.addWidget(self.stream_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.stream_status = QLabel('')
        self.stream_status.setObjectName('status-dim')
        layout.addWidget(self.stream_status)

        layout.addWidget(_hline())

        layout.addWidget(_section('Viewer Link'))

        self.url_label = QLabel('—')
        self.url_label.setObjectName('url-label')
        layout.addWidget(self.url_label)

        link_btns = QHBoxLayout()
        self.copy_btn = QPushButton('Copy URL')
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_url)
        self.open_btn = QPushButton('Open in Browser')
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_browser)
        link_btns.addWidget(self.copy_btn)
        link_btns.addWidget(self.open_btn)
        link_btns.addStretch()
        layout.addLayout(link_btns)

        note = QLabel(
            'Share the URL with anyone on your local network.\n'
            'Works in VLC (Media → Open Network Stream) or any web browser.\n'
            'Stream auto-restarts every ~3 minutes (Android screenrecord limit).'
        )
        note.setObjectName('status-dim')
        note.setWordWrap(True)
        layout.addWidget(note)

        deps = QLabel('')
        missing = []
        if not shutil.which('ffmpeg'):
            missing.append('ffmpeg')
        if missing:
            deps.setText(f'⚠  Missing: {", ".join(missing)} — install with: brew install {" ".join(missing)}')
            deps.setObjectName('status-err')
        layout.addWidget(deps)

        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _toggle(self):
        if self.streamer.is_running():
            self._stop()
        else:
            self._start()

    def _start(self):
        if not self._serial:
            return
        adb_path = self.adb.path
        ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        ok, result = self.streamer.start(
            serial=self._serial,
            adb_path=adb_path,
            ffmpeg_path=ffmpeg_path,
            bitrate=self.bitrate_combo.currentData(),
            resolution=self.res_combo.currentData(),
            port=self.port_spin.value(),
        )
        if ok:
            self._url = result
            self.url_label.setText(result)
            self.stream_btn.setText('■  STOP STREAM')
            self.stream_btn.setObjectName('btn-stop')
            self.stream_btn.setStyleSheet('')
            self.copy_btn.setEnabled(True)
            self.open_btn.setEnabled(True)
            self.stream_status.setText('Streaming…')
            self.stream_status.setObjectName('status-ok')
        else:
            self.stream_status.setText(f'Failed: {result}')
            self.stream_status.setObjectName('status-err')
        self.stream_status.setStyleSheet('')

    def _stop(self):
        self.streamer.stop()
        self._url = ''
        self.url_label.setText('—')
        self.stream_btn.setText('▶  START STREAM')
        self.stream_btn.setObjectName('btn-primary')
        self.stream_btn.setStyleSheet('')
        self.stream_btn.setEnabled(bool(self._serial))
        self.copy_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.stream_status.setText('Stream stopped')
        self.stream_status.setObjectName('status-dim')
        self.stream_status.setStyleSheet('')

    def _copy_url(self):
        try:
            import pyperclip
            pyperclip.copy(self._url)
            self.stream_status.setText('URL copied to clipboard')
        except Exception:
            self.stream_status.setText(self._url)

    def _open_browser(self):
        if self._url:
            open_url(self._url)
