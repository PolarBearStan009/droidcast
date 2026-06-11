import os
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTabWidget,
    QSplitter, QStatusBar, QSystemTrayIcon, QMenu, QDialog,
    QLineEdit, QDialogButtonBox, QFormLayout, QMessageBox,
)

from core.adb import ADB, Device
from core.scrcpy import ScrcpyManager
from core.streamer import Streamer
from ui.panels.mirror import MirrorPanel
from ui.panels.record import RecordPanel
from ui.panels.stream import StreamPanel
from ui.panels.files import FilesPanel
from ui.panels.settings import SettingsPanel


def _make_tray_icon() -> QIcon:
    px = QPixmap(32, 32)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setBrush(QColor('#8B0000'))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 28, 28)
    p.setPen(QColor('#e0e0e0'))
    p.setFont(p.font())
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, 'D')
    p.end()
    return QIcon(px)


class DevicePoller(QThread):
    updated = pyqtSignal(list)

    def __init__(self, adb: ADB):
        super().__init__()
        self._adb = adb
        self._running = True

    def run(self):
        while self._running:
            try:
                devices = self._adb.devices()
            except Exception:
                devices = []
            self.updated.emit(devices)
            self.msleep(2500)

    def stop(self):
        self._running = False


class WiFiDialog(QDialog):
    def __init__(self, adb: ADB, serial: str, parent=None):
        super().__init__(parent)
        self.adb = adb
        self.serial = serial
        self.setWindowTitle('Connect via WiFi')
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText('192.168.x.x')
        form.addRow('Phone IP:', self.ip_input)
        layout.addLayout(form)

        self.status = QLabel('Click "Enable WiFi ADB" first if connecting for the first time.')
        self.status.setObjectName('status-dim')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        btns = QHBoxLayout()
        self.enable_btn = QPushButton('Enable WiFi ADB')
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.setObjectName('btn-primary')
        btns.addWidget(self.enable_btn)
        btns.addWidget(self.connect_btn)
        layout.addLayout(btns)

        self.enable_btn.clicked.connect(self._enable)
        self.connect_btn.clicked.connect(self._connect)

    def _enable(self):
        self.status.setText('Enabling WiFi ADB...')
        ok = self.adb.wifi_enable(self.serial)
        ip = self.adb.wifi_ip(self.serial)
        if ok:
            msg = 'WiFi ADB enabled on port 5555.'
            if ip:
                msg += f'\nDetected IP: {ip}'
                self.ip_input.setText(ip)
            self.status.setText(msg)
            self.status.setObjectName('status-ok')
        else:
            self.status.setText('Failed to enable WiFi ADB.')
            self.status.setObjectName('status-err')
        self.status.setStyleSheet('')

    def _connect(self):
        ip = self.ip_input.text().strip()
        if not ip:
            self.status.setText('Enter an IP address.')
            return
        self.status.setText(f'Connecting to {ip}:5555...')
        ok, msg = self.adb.wifi_connect(ip)
        self.status.setText(msg)
        if ok:
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('Droidcast', 'Droidcast')
        self.adb = ADB(self.settings.value('adb_path', ''))
        self.scrcpy = ScrcpyManager(self.settings.value('scrcpy_path', ''))
        self.streamer = Streamer()
        self._selected_serial = ''
        self._devices: list[Device] = []

        self.setWindowTitle('Droidcast')
        self.setMinimumSize(820, 580)
        self.resize(
            int(self.settings.value('win_w', 960)),
            int(self.settings.value('win_h', 640)),
        )

        self._build_ui()
        self._build_tray()
        self._start_poller()

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        self.setCentralWidget(splitter)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 8)
        sb_layout.setSpacing(0)

        title = QLabel('DEVICES')
        title.setObjectName('sidebar-title')
        sb_layout.addWidget(title)

        self.device_list = QListWidget()
        self.device_list.setObjectName('device-list')
        self.device_list.currentRowChanged.connect(self._on_device_selected)
        sb_layout.addWidget(self.device_list, 1)

        self.device_info = QLabel('No device selected')
        self.device_info.setObjectName('status-dim')
        self.device_info.setWordWrap(True)
        self.device_info.setContentsMargins(12, 6, 12, 6)
        sb_layout.addWidget(self.device_info)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 4, 8, 4)

        self.refresh_btn = QPushButton('⟳ Refresh')
        self.refresh_btn.setToolTip('Rescan ADB devices')
        self.refresh_btn.clicked.connect(self._refresh_devices)
        btn_row.addWidget(self.refresh_btn)

        self.wifi_btn = QPushButton('WiFi')
        self.wifi_btn.setToolTip('Connect device over WiFi')
        self.wifi_btn.setEnabled(False)
        self.wifi_btn.clicked.connect(self._wifi_dialog)
        btn_row.addWidget(self.wifi_btn)

        sb_layout.addLayout(btn_row)
        splitter.addWidget(sidebar)

        # ── Right panel ───────────────────────────────────────
        right = QWidget()
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.mirror_panel = MirrorPanel(self.adb, self.scrcpy, self.settings)
        self.record_panel = RecordPanel(self.scrcpy, self.settings)
        self.stream_panel = StreamPanel(self.adb, self.streamer, self.settings)
        self.files_panel = FilesPanel(self.adb)
        self.settings_panel = SettingsPanel(self.settings, self.adb, self.scrcpy)

        self.tabs.addTab(self.mirror_panel, 'Mirror')
        self.tabs.addTab(self.record_panel, 'Record')
        self.tabs.addTab(self.stream_panel, 'Stream')
        self.tabs.addTab(self.files_panel, 'Files')
        self.tabs.addTab(self.settings_panel, '⚙  Settings')

        r_layout.addWidget(self.tabs)
        splitter.addWidget(right)
        splitter.setSizes([210, 750])

        # ── Status bar ────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status('No device connected')

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = _make_tray_icon()
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        show_act = QAction('Show', self)
        quit_act = QAction('Quit', self)
        show_act.triggered.connect(self.show)
        quit_act.triggered.connect(self._quit)
        menu.addAction(show_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _start_poller(self):
        self._poller = DevicePoller(self.adb)
        self._poller.updated.connect(self._on_devices_updated)
        self._poller.start()

    def _on_devices_updated(self, devices: list):
        prev_serial = self._selected_serial
        self._devices = devices

        self.device_list.blockSignals(True)
        self.device_list.clear()
        restore_row = -1

        for i, d in enumerate(devices):
            icon = '●' if d.state == 'device' else '○'
            label = f'{icon}  {d.model or d.serial}'
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, d.serial)
            if d.state != 'device':
                item.setForeground(QColor('#555'))
            self.device_list.addItem(item)
            if d.serial == prev_serial:
                restore_row = i

        self.device_list.blockSignals(False)

        if restore_row >= 0:
            self.device_list.setCurrentRow(restore_row)
        elif devices:
            self.device_list.setCurrentRow(0)
        else:
            self._selected_serial = ''
            self._propagate_device('')
            self._set_status('No device connected')
            self.device_info.setText('No device selected')

    def _on_device_selected(self, row: int):
        if row < 0 or row >= len(self._devices):
            return
        d = self._devices[row]
        self._selected_serial = d.serial
        self.wifi_btn.setEnabled(d.state == 'device')
        self._propagate_device(d.serial if d.state == 'device' else '')

        if d.state == 'device':
            self._set_status(f'Connected: {d.model or d.serial}')
            info = self.adb.device_info(d.serial)
            parts = []
            if info.get('model'):
                parts.append(info['model'])
            if info.get('android'):
                parts.append(f'Android {info["android"]}')
            if info.get('battery', -1) >= 0:
                parts.append(f'🔋 {info["battery"]}%')
            if info.get('resolution'):
                parts.append(info['resolution'])
            self.device_info.setText('\n'.join(parts))
        else:
            self._set_status(f'{d.serial} — {d.state}')
            self.device_info.setText(f'{d.serial}\n{d.state}')

    def _propagate_device(self, serial: str):
        for panel in (self.mirror_panel, self.record_panel,
                      self.stream_panel, self.files_panel):
            panel.set_device(serial)

    def _refresh_devices(self):
        self._on_devices_updated(self.adb.devices())

    def _wifi_dialog(self):
        if not self._selected_serial:
            return
        dlg = WiFiDialog(self.adb, self._selected_serial, self)
        dlg.exec()
        self._refresh_devices()

    def _set_status(self, msg: str):
        self.status_bar.showMessage(msg)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit(self):
        self.scrcpy.stop()
        self.streamer.stop()
        if hasattr(self, '_poller'):
            self._poller.stop()
        self.close()

    def closeEvent(self, event):
        minimize_to_tray = self.settings.value('minimize_to_tray', False, type=bool)
        if minimize_to_tray and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
        else:
            self.settings.setValue('win_w', self.width())
            self.settings.setValue('win_h', self.height())
            self.scrcpy.stop()
            self.streamer.stop()
            if hasattr(self, '_poller'):
                self._poller.stop()
            event.accept()
