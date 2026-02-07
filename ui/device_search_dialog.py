from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRunnable, QThreadPool
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QHeaderView,
    QLineEdit,
)

from backend.device_list_loader import DeviceListLoader


class _PrefixWorker(QObject):
    done = Signal(list)


class _PrefixTask(QRunnable):
    def __init__(self, loader: DeviceListLoader, sink: _PrefixWorker):
        super().__init__()
        self.loader = loader
        self.sink = sink

    def run(self):
        prefixes = self.loader.compute_prefixes()
        self.sink.done.emit(prefixes)


class DeviceSearchDialog(QDialog):
    def __init__(self, loader: DeviceListLoader, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select IC")
        self.resize(980, 560)

        self.loader = loader
        self.selected_chip: str = ""

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        root.addLayout(top)
        top.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type chip model (min 2 chars), e.g. 93C86C, W25Q64…")
        top.addWidget(self.search_edit, 1)

        row = QHBoxLayout()
        root.addLayout(row)

        self.tbl_prefix = QTableWidget(0, 1)
        self.tbl_prefix.setHorizontalHeaderLabels(["Prefix"])
        self.tbl_prefix.verticalHeader().setVisible(False)
        self.tbl_prefix.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_prefix.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_prefix.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_prefix.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.tbl_chips = QTableWidget(0, 1)
        self.tbl_chips.setHorizontalHeaderLabels(["Chip"])
        self.tbl_chips.verticalHeader().setVisible(False)
        self.tbl_chips.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_chips.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_chips.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_chips.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.info = QLabel("Short information:\n")
        self.info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info.setStyleSheet("QLabel { font-family: Menlo, Monaco, Consolas, monospace; font-size: 11px; }")

        row.addWidget(self.tbl_prefix, 1)
        row.addWidget(self.tbl_chips, 3)
        row.addWidget(self.info, 4)

        bottom = QHBoxLayout()
        root.addLayout(bottom)
        bottom.addStretch(1)

        self.btn_confirm = QPushButton("Confirm choice")
        self.btn_cancel = QPushButton("Cancel")
        bottom.addWidget(self.btn_confirm)
        bottom.addWidget(self.btn_cancel)

        self.btn_confirm.clicked.connect(self._confirm)
        self.btn_cancel.clicked.connect(self.reject)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._apply_search)

        self.search_edit.textChanged.connect(lambda *_: self._search_timer.start())

        self.tbl_prefix.itemSelectionChanged.connect(self._on_prefix_changed)
        self.tbl_chips.itemSelectionChanged.connect(self._on_chip_changed)
        self.tbl_chips.itemDoubleClicked.connect(lambda *_: self._confirm())

        self._fill_prefixes_loading()
        self._load_prefixes_async()

    def _fill_prefixes_loading(self) -> None:
        self.tbl_prefix.blockSignals(True)
        self.tbl_prefix.setRowCount(0)
        self.tbl_prefix.insertRow(0)
        self.tbl_prefix.setItem(0, 0, QTableWidgetItem("Loading…"))
        self.tbl_prefix.blockSignals(False)

    def _load_prefixes_async(self) -> None:
        self._prefix_sink = _PrefixWorker()
        self._prefix_sink.done.connect(self._set_prefixes)
        QThreadPool.globalInstance().start(_PrefixTask(self.loader, self._prefix_sink))

    def _set_prefixes(self, prefixes: list) -> None:
        if not prefixes:
            prefixes = ["A"]

        self.tbl_prefix.blockSignals(True)
        self.tbl_prefix.setRowCount(0)

        for p in prefixes:
            r = self.tbl_prefix.rowCount()
            self.tbl_prefix.insertRow(r)
            it = QTableWidgetItem(str(p))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_prefix.setItem(r, 0, it)

        self.tbl_prefix.blockSignals(False)

        self.tbl_prefix.selectRow(0)
        self._load_chips_for_prefix(str(prefixes[0]))

    def _load_chips_for_prefix(self, prefix_char: str) -> None:
        p = (prefix_char or "").strip()
        if not p:
            return
        p = p[0]  # строго один символ
        chips = self.loader.list_by_prefix(p)
        self._set_chip_table(chips)

    def _set_chip_table(self, chips: list[str]) -> None:
        self.tbl_chips.blockSignals(True)
        self.tbl_chips.setRowCount(0)

        for chip in chips:
            r = self.tbl_chips.rowCount()
            self.tbl_chips.insertRow(r)
            it = QTableWidgetItem(chip)
            it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.tbl_chips.setItem(r, 0, it)

        self.tbl_chips.blockSignals(False)

        self.selected_chip = ""
        self.info.setText("Short information:\n")

        if self.tbl_chips.rowCount() > 0:
            self.tbl_chips.selectRow(0)
            self._on_chip_changed()

    def _apply_search(self) -> None:
        q = (self.search_edit.text() or "").strip()
        if len(q) < 2:
            self.tbl_prefix.setEnabled(True)
            items = self.tbl_prefix.selectedItems()
            if items:
                self._load_chips_for_prefix(items[0].text())
            return

        self.tbl_prefix.setEnabled(False)
        chips = self.loader.search(q)
        self._set_chip_table(chips)

    def _on_prefix_changed(self) -> None:
        q = (self.search_edit.text() or "").strip()
        if len(q) >= 2:
            return

        items = self.tbl_prefix.selectedItems()
        if not items:
            return
        self._load_chips_for_prefix(items[0].text())

    def _on_chip_changed(self) -> None:
        items = self.tbl_chips.selectedItems()
        if not items:
            self.selected_chip = ""
            self.info.setText("Short information:\n")
            return

        chip = items[0].text().strip()
        self.selected_chip = chip

        info = self.loader.get_info(chip)
        text = "Short information:\n" + (info.short or "")
        self.info.setText(text)

    def _confirm(self) -> None:
        if not self.selected_chip:
            return
        self.accept()
