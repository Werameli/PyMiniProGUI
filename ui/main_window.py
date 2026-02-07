from __future__ import annotations

import os
import shutil
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QCheckBox,
    QMessageBox,
    QDialog,
    QFrame,
    QSizePolicy,
)

from ui.strings import S
from backend.minipro_backend import MiniProBackend, WriteOptions
from ui.device_search_dialog import DeviceSearchDialog
from ui.hex_view import HexView
from ui.about_dialog import AboutDialog


def _parse_chip_info_lines(info_text: str) -> dict:
    out = {
        "memory": "",
        "package": "",
        "protocol": "",
        "read_buffer": "",
        "write_buffer": "",
    }
    if not info_text:
        return out

    for ln in info_text.splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()

        if low.startswith("memory:"):
            out["memory"] = s.split(":", 1)[1].strip() if ":" in s else ""
        elif low.startswith("package:"):
            out["package"] = s.split(":", 1)[1].strip() if ":" in s else ""
        elif low.startswith("protocol:"):
            out["protocol"] = s.split(":", 1)[1].strip() if ":" in s else ""
        elif low.startswith("read buffer"):
            out["read_buffer"] = s.split(":", 1)[1].strip() if ":" in s else s
        elif low.startswith("write buffer"):
            out["write_buffer"] = s.split(":", 1)[1].strip() if ":" in s else s

    return out


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(S.APP_NAME)

        self.backend = MiniProBackend(minipro_path="minipro")

        self.prog_label = QLabel(f"{S.LBL_PROGRAMMER_PREFIX} Unknown")
        self.reload_btn = QPushButton(S.BTN_RELOAD)
        self.update_fw_btn = QPushButton(S.BTN_UPGRADE_FW)
        self.about_btn = QPushButton(S.BTN_ABOUT)

        self.auto_detect_btn = QPushButton(S.BTN_AUTO_DETECT)
        self.select_ic_btn = QPushButton(S.BTN_SELECT_IC)

        def mk_value_row() -> QLabel:
            v = QLabel("")
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            # Let the layout control the width so the value fields don't get clipped
            # or overlap when the window is resized.
            v.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            v.setMinimumHeight(30)
            v.setMinimumWidth(260)
            v.setWordWrap(False)
            v.setStyleSheet(
                "QLabel {"
                "  background: rgba(255,255,255,0.06);"
                "  padding: 6px 10px;"
                "  border-radius: 8px;"
                "  font-family: Menlo, Monaco, Consolas, monospace;"
                "  font-size: 11px;"
                "}"
            )
            return v

        self.val_device = mk_value_row()
        self.val_memory = mk_value_row()
        self.val_package = mk_value_row()
        self.val_protocol = mk_value_row()
        self.val_rbuf = mk_value_row()
        self.val_wbuf = mk_value_row()

        self.pkg_image = QLabel("")
        self.pkg_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pkg_image.setFixedWidth(160)
        self.pkg_image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.pkg_image.setMinimumHeight(160)

        self.cb_ignore_id = QCheckBox(S.CB_IGNORE_ID)
        self.cb_ignore_size = QCheckBox(S.CB_IGNORE_SIZE)
        self.cb_skip_id = QCheckBox(S.CB_SKIP_ID)
        self.cb_skip_verify = QCheckBox(S.CB_SKIP_VERIFY)

        self.read_btn = QPushButton(S.BTN_READ)
        self.write_btn = QPushButton(S.BTN_WRITE)
        self.save_dump_btn = QPushButton(S.BTN_SAVE_DUMP)
        self.save_dump_btn.setEnabled(False)

        self.pin_check_btn = QPushButton(S.BTN_PIN)
        self.blank_check_btn = QPushButton(S.BTN_BLANK)
        self.erase_btn = QPushButton(S.BTN_ERASE)
        self.hardware_check_btn = QPushButton(S.BTN_HW)

        self.hex_view = HexView()
        self.hex_view.show_empty(rows=16)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        outer.addLayout(left_col, 1)

        gb_targets = QGroupBox(S.GB_TARGETS)
        lt_targets = QVBoxLayout(gb_targets)
        lt_targets.setSpacing(8)

        self.prog_label.setStyleSheet("QLabel { font-weight: 600; }")
        lt_targets.addWidget(self.prog_label)
        lt_targets.addWidget(self.reload_btn)
        lt_targets.addWidget(self.update_fw_btn)
        lt_targets.addWidget(self.about_btn)
        left_col.addWidget(gb_targets, 0)

        gb_ops = QGroupBox(S.GB_OPERATIONS)
        lt_ops = QVBoxLayout(gb_ops)
        lt_ops.setSpacing(8)

        opt_grid = QGridLayout()
        opt_grid.setHorizontalSpacing(16)
        opt_grid.setVerticalSpacing(8)
        opt_grid.addWidget(self.cb_ignore_id, 0, 0)
        opt_grid.addWidget(self.cb_ignore_size, 0, 1)
        opt_grid.addWidget(self.cb_skip_id, 1, 0)
        opt_grid.addWidget(self.cb_skip_verify, 1, 1)
        lt_ops.addLayout(opt_grid)

        lt_ops.addWidget(self.read_btn)
        lt_ops.addWidget(self.write_btn)
        lt_ops.addWidget(self.save_dump_btn)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)
        lt_ops.addWidget(div)

        lt_ops.addWidget(self.pin_check_btn)
        lt_ops.addWidget(self.blank_check_btn)
        lt_ops.addWidget(self.erase_btn)
        lt_ops.addWidget(self.hardware_check_btn)

        left_col.addWidget(gb_ops, 0)

        gb_out = QGroupBox(S.GB_OUTPUT)
        lt_out = QVBoxLayout(gb_out)
        lt_out.setContentsMargins(8, 8, 8, 8)
        lt_out.addWidget(self.log)
        left_col.addWidget(gb_out, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        outer.addLayout(right_col, 2)

        gb_devinfo = QGroupBox(S.GB_DEVICE_INFO)
        lt_dev_outer = QVBoxLayout(gb_devinfo)
        lt_dev_outer.setSpacing(12)
        # Add comfortable padding so rounded corners aren't clipped by the group box.
        lt_dev_outer.setContentsMargins(12, 18, 12, 12)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.auto_detect_btn)
        btn_row.addWidget(self.select_ic_btn)
        btn_row.addStretch(1)
        lt_dev_outer.addLayout(btn_row)

        body = QHBoxLayout()
        body.setSpacing(12)
        lt_dev_outer.addLayout(body)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        # Column 1 contains the value fields — let it expand.
        grid.setColumnStretch(1, 1)

        def add_row(r: int, label: str, widget: QLabel) -> None:
            l = QLabel(label)
            l.setMinimumWidth(92)
            l.setMinimumHeight(22)
            l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(l, r, 0)
            grid.addWidget(widget, r, 1)

        add_row(0, S.DI_DEVICE, self.val_device)
        add_row(1, S.DI_MEMORY, self.val_memory)
        add_row(2, S.DI_PACKAGE, self.val_package)
        add_row(3, S.DI_PROTOCOL, self.val_protocol)
        add_row(4, S.DI_READ_BUF, self.val_rbuf)
        add_row(5, S.DI_WRITE_BUF, self.val_wbuf)

        grid_wrap = QWidget()
        grid_wrap.setLayout(grid)
        body.addWidget(grid_wrap, 1)
        body.addWidget(self.pkg_image, 0)

        right_col.addWidget(gb_devinfo, 0)

        gb_hex = QGroupBox(S.GB_HEX)
        lt_hex = QVBoxLayout(gb_hex)
        lt_hex.setContentsMargins(8, 8, 8, 8)
        lt_hex.addWidget(self.hex_view)
        right_col.addWidget(gb_hex, 1)

        self.reload_btn.clicked.connect(self.backend.reload)
        self.auto_detect_btn.clicked.connect(self.backend.auto_detect_chip)
        self.select_ic_btn.clicked.connect(self.on_select_ic)
        self.update_fw_btn.clicked.connect(self.on_update_fw)
        self.about_btn.clicked.connect(self.on_about)

        self.read_btn.clicked.connect(self.on_read_tmp)
        self.save_dump_btn.clicked.connect(self.on_save_dump)
        self.write_btn.clicked.connect(self.on_write_with_confirm)

        self.blank_check_btn.clicked.connect(self.backend.blank_check)
        self.erase_btn.clicked.connect(self.backend.erase_chip)
        self.pin_check_btn.clicked.connect(self.on_pin_check)
        self.hardware_check_btn.clicked.connect(self.on_hardware_check)

        self.backend.log.connect(self.append_log_live)
        self.backend.programmerChanged.connect(self.on_programmer_changed)
        self.backend.chipChanged.connect(self.on_chip_changed)
        self.backend.chipInfoChanged.connect(self.on_chip_info_changed)
        self.backend.operationFinished.connect(self.on_op_finished)

        self.backend.reload()

    def on_about(self) -> None:
        AboutDialog(self).exec()

    def append_log_live(self, chunk: str) -> None:
        if not chunk:
            return
        cur = self.log.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(chunk)
        self.log.setTextCursor(cur)
        self.log.ensureCursorVisible()

    def on_programmer_changed(self, p: str) -> None:
        self.prog_label.setText(f"{S.LBL_PROGRAMMER_PREFIX} {p}")
        self.append_log_live(f"\n[ui] programmer: {p}\n")

    def on_chip_changed(self, chip: str) -> None:
        self.val_device.setText(chip or "<none>")
        self._set_package_image_from_chip(chip)

    def on_chip_info_changed(self, txt: str) -> None:
        chip = self.backend.current_chip or ""
        parsed = _parse_chip_info_lines(txt or "")

        self.val_device.setText(chip or "<none>")
        self.val_memory.setText(parsed.get("memory", ""))
        pkg_from_chip = chip.split("@", 1)[1].strip() if chip and "@" in chip else ""
        self.val_package.setText(pkg_from_chip or parsed.get("package", ""))
        self.val_protocol.setText(parsed.get("protocol", ""))
        self.val_rbuf.setText(parsed.get("read_buffer", ""))
        self.val_wbuf.setText(parsed.get("write_buffer", ""))

    def on_op_finished(self, ok: bool, msg: str) -> None:
        self.append_log_live(f"\n[ui] {msg}\n")
        if ok:
            tmp = self.backend.last_dump_path
            if tmp and os.path.exists(tmp) and msg.startswith("Read OK"):
                self.hex_view.load_file(tmp)
                self.save_dump_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "Operation", msg)

    def on_select_ic(self) -> None:
        dlg = DeviceSearchDialog(self.backend.loader, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.backend.set_chip(dlg.selected_chip)

    def on_update_fw(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select update.dat", "", "update.dat (update.dat);;All files (*)"
        )
        if not path:
            return
        self.backend.update_firmware(path)

    def on_read_tmp(self) -> None:
        if not self.backend.current_chip:
            QMessageBox.warning(self, "Read", "No chip selected")
            return
        self.backend.read_to_tmp()

    def on_save_dump(self) -> None:
        tmp_path = self.backend.last_dump_path or os.path.join(tempfile.gettempdir(), "dump.bin")
        if not os.path.exists(tmp_path):
            QMessageBox.information(self, "Save dump", "No dump.bin in tmp yet. Use Read first.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save dump as…", "dump.bin", "Binary (*.bin);;All files (*)"
        )
        if not out_path:
            return
        try:
            shutil.copyfile(tmp_path, out_path)
            self.append_log_live(f"[ui] saved dump: {out_path}\n")
        except Exception as e:
            QMessageBox.warning(self, "Save dump", f"Failed to save: {e}")

    def on_write_with_confirm(self) -> None:
        if not self.backend.current_chip:
            QMessageBox.warning(self, "Write", "No chip selected")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Select file to write…", "", "Binary (*.bin *.rom *.img);;All files (*)"
        )
        if not path:
            return

        self.hex_view.load_file(path)

        chip = self.backend.current_chip
        resp = QMessageBox.question(
            self,
            "Confirm Write",
            f"Write file:\n{os.path.basename(path)}\n\nTo chip:\n{chip}\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            self.append_log_live("[ui] write cancelled by user\n")
            return

        opts = WriteOptions(
            erase_before_write=True,
            skip_verification=self.cb_skip_verify.isChecked(),
        )

        for k, v in {
            "ignore_id_error": self.cb_ignore_id.isChecked(),
            "ignore_size_error": self.cb_ignore_size.isChecked(),
            "skip_id_check": self.cb_skip_id.isChecked(),
        }.items():
            try:
                setattr(opts, k, v)
            except Exception:
                pass

        self.backend.write_chip(path, opts)

    def on_pin_check(self) -> None:
        if not self.backend.current_chip:
            QMessageBox.warning(self, "Pin Check", "No chip selected")
            return
        if hasattr(self.backend, "pin_check"):
            self.backend.pin_check()
        else:
            QMessageBox.information(self, "Pin Check", "Pin Check is not implemented in backend yet.")

    def on_hardware_check(self) -> None:
        if hasattr(self.backend, "hardware_check"):
            self.backend.hardware_check()
        else:
            QMessageBox.information(
                self, "Hardware Check", "Hardware Check is not implemented in backend yet."
            )

    def _set_package_image_from_chip(self, chip: str) -> None:
        pkg = chip.split("@", 1)[1].strip() if chip and "@" in chip else ""
        if not pkg:
            self.pkg_image.setPixmap(QPixmap())
            self.pkg_image.setText("")
            return

        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        img_path = os.path.join(assets_dir, f"{pkg}.png")

        if os.path.exists(img_path):
            pm = QPixmap(img_path).scaledToWidth(150, Qt.TransformationMode.SmoothTransformation)
            self.pkg_image.setPixmap(pm)
            self.pkg_image.setText("")
        else:
            self.pkg_image.setPixmap(QPixmap())
            self.pkg_image.setText("")
