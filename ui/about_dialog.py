from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from ui.strings import S


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(S.ABOUT_TITLE)
        self.setModal(True)
        self.setMinimumWidth(500)

        title = QLabel(f"{S.APP_NAME}")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: 700; }")

        body = QLabel(S.ABOUT_TEXT)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setWordWrap(True)

        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(ok)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(title)
        lay.addWidget(body)
        lay.addLayout(btn_row)
