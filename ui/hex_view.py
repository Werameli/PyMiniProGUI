from __future__ import annotations

import os
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView


def _byte_to_ascii(b: int) -> str:
    return chr(b) if 32 <= b <= 126 else "."


class HexView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data: bytes = b""

        self.table = QTableWidget(self)
        self.table.setColumnCount(17)  # 16 bytes + ASCII
        self.table.setHorizontalHeaderLabels([f"{i:02X}" for i in range(16)] + ["ASCII"])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        f = QFont("Menlo", 11)
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.table.setFont(f)

        hh = self.table.horizontalHeader()
        for c in range(16):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(16, QHeaderView.ResizeMode.Stretch)

        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setDefaultSectionSize(22)
        vh.setMinimumWidth(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)

        self.show_empty(rows=8)

    def show_empty(self, rows: int = 8, fill_hex: str = "FF", fill_ascii: str = ".") -> None:
        rows = max(1, int(rows))
        self._data = b""

        self.table.setRowCount(rows)
        for r in range(rows):
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

            for c in range(16):
                it = QTableWidgetItem(fill_hex)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, it)

            ascii_it = QTableWidgetItem(fill_ascii * 16)
            ascii_it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 16, ascii_it)

        self.table.scrollToTop()

    def load_file(self, path: str, min_rows: int = 8) -> None:
        path = (path or "").strip()
        if not path or not os.path.exists(path):
            self.show_empty(rows=min_rows)
            return

        with open(path, "rb") as f:
            self.load_bytes(f.read(), min_rows=min_rows)

    def load_bytes(self, data: bytes, min_rows: int = 8) -> None:
        data = data or b""
        self._data = data

        rows_needed = max(min_rows, int(math.ceil(len(data) / 16.0)) if len(data) else min_rows)
        self.table.setRowCount(rows_needed)

        for r in range(rows_needed):
            self.table.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

            base = r * 16
            ascii_chars = []

            for c in range(16):
                idx = base + c
                if idx < len(data):
                    b = data[idx]
                    hex_text = f"{b:02X}"
                    ascii_chars.append(_byte_to_ascii(b))
                else:
                    hex_text = "FF"
                    ascii_chars.append(".")

                it = QTableWidgetItem(hex_text)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, it)

            ascii_it = QTableWidgetItem("".join(ascii_chars))
            ascii_it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 16, ascii_it)

        self.table.scrollToTop()

    def data(self) -> bytes:
        return self._data
