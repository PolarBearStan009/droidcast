import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QFrame, QMessageBox, QAbstractItemView,
)

from core.adb import ADB


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section-title')
    return lbl


class FilesPanel(QWidget):
    def __init__(self, adb: ADB):
        super().__init__()
        self.adb = adb
        self._serial = ''
        self._path = '/sdcard'
        self._history: list[str] = []
        self._build_ui()

    def set_device(self, serial: str):
        self._serial = serial
        enabled = bool(serial)
        self.push_btn.setEnabled(enabled)
        self.pull_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.back_btn.setEnabled(enabled and bool(self._history))
        if enabled:
            self._load()
        else:
            self.table.setRowCount(0)
            self.path_label.setText('—')

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(_section('File Transfer'))

        nav = QHBoxLayout()
        self.back_btn = QPushButton('← Back')
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self._go_back)
        self.path_label = QLabel('/sdcard')
        self.path_label.setObjectName('status-dim')
        self.refresh_btn = QPushButton('⟳')
        self.refresh_btn.setFixedWidth(36)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._load)
        nav.addWidget(self.back_btn)
        nav.addWidget(self.path_label, 1)
        nav.addWidget(self.refresh_btn)
        layout.addLayout(nav)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Name', 'Size', 'Type'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

        self.status = QLabel('')
        self.status.setObjectName('status-dim')
        layout.addWidget(self.status)

        btn_row = QHBoxLayout()
        self.push_btn = QPushButton('↑  Push File to Phone')
        self.push_btn.setEnabled(False)
        self.push_btn.clicked.connect(self._push)

        self.pull_btn = QPushButton('↓  Pull Selected File')
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self._pull)

        self.delete_btn = QPushButton('🗑  Delete')
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete)
        self.table.itemSelectionChanged.connect(
            lambda: self.delete_btn.setEnabled(
                bool(self._serial) and self.table.currentRow() >= 0
            )
        )

        btn_row.addWidget(self.push_btn)
        btn_row.addWidget(self.pull_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _load(self):
        if not self._serial:
            return
        self.status.setText(f'Loading {self._path}…')
        entries = self.adb.list_dir(self._serial, self._path)
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            icon = '📁' if entry['is_dir'] else '📄'
            name_item = QTableWidgetItem(f'{icon}  {entry["name"]}')
            name_item.setData(Qt.ItemDataRole.UserRole, entry)
            size_str = (
                '' if entry['is_dir']
                else f'{entry["size"] / 1024:.1f} KB' if entry['size'] < 1_048_576
                else f'{entry["size"] / 1_048_576:.1f} MB'
            )
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(size_str))
            self.table.setItem(row, 2, QTableWidgetItem('Folder' if entry['is_dir'] else 'File'))
        self.path_label.setText(self._path)
        self.status.setText(f'{len(entries)} items')

    def _on_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry and entry.get('is_dir'):
            self._history.append(self._path)
            self._path = f'{self._path}/{entry["name"]}'
            self.back_btn.setEnabled(True)
            self._load()

    def _go_back(self):
        if self._history:
            self._path = self._history.pop()
            self.back_btn.setEnabled(bool(self._history))
            self._load()

    def _push(self):
        local, _ = QFileDialog.getOpenFileName(self, 'Choose file to push')
        if not local:
            return
        remote = f'{self._path}/{os.path.basename(local)}'
        self.status.setText(f'Pushing {os.path.basename(local)}…')
        ok, msg = self.adb.push(self._serial, local, remote)
        self.status.setText(msg if not ok else f'Pushed → {remote}')
        if ok:
            self._load()

    def _pull(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry['is_dir']:
            self.status.setText('Select a file, not a folder.')
            return
        remote = f'{self._path}/{entry["name"]}'
        local_dir = QFileDialog.getExistingDirectory(self, 'Save to folder')
        if not local_dir:
            return
        local = os.path.join(local_dir, entry['name'])
        self.status.setText(f'Pulling {entry["name"]}…')
        ok, msg = self.adb.pull(self._serial, remote, local)
        self.status.setText(msg if not ok else f'Saved → {local}')

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        entry = item.data(Qt.ItemDataRole.UserRole)
        remote = f'{self._path}/{entry["name"]}'
        reply = QMessageBox.question(
            self, 'Delete', f'Delete {remote}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = self.adb.delete(self._serial, remote)
            self.status.setText('Deleted.' if ok else 'Delete failed.')
            if ok:
                self._load()
