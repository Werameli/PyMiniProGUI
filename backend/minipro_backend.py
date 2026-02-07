from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

from .pty_runner import run_tty_stream
from .device_list_loader import DeviceListLoader, ChipInfo


def _ensure_path_for_gui_apps() -> None:
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(":") if p]

    candidates = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        "/opt/local/bin",
    ]

    for c in candidates:
        if c not in parts and os.path.isdir(c):
            parts.insert(0, c)

    os.environ["PATH"] = ":".join(parts)


def _resolve_minipro(minipro_path: str) -> str:
    mp = (minipro_path or "").strip() or "minipro"

    if os.path.sep in mp or mp.startswith("."):
        if os.path.exists(mp):
            return mp
        mp2 = os.path.abspath(mp)
        if os.path.exists(mp2):
            return mp2

    found = shutil.which(mp)
    if found:
        return found

    found2 = shutil.which("minipro")
    if found2:
        return found2

    return mp


class _Runnable(QRunnable):
    def __init__(self, fn: Callable[[], None]):
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        self._fn()


@dataclass
class WriteOptions:
    erase_before_write: bool = True
    skip_verification: bool = False


class MiniProBackend(QObject):
    log = Signal(str)
    programmerChanged = Signal(str)
    chipChanged = Signal(str)
    chipInfoChanged = Signal(str)
    operationFinished = Signal(bool, str)

    def __init__(self, minipro_path: str = "minipro"):
        super().__init__()

        _ensure_path_for_gui_apps()

        self.minipro_path = _resolve_minipro(minipro_path)

        self.loader = DeviceListLoader(minipro_path=self.minipro_path)

        self.pool = QThreadPool.globalInstance()

        self.current_chip: str = ""
        self.last_dump_path: str = ""
        self.last_chip_id: str = ""

        self._emit(f"[init] minipro path: {self.minipro_path}\n")
        self._emit(f"[init] PATH: {os.environ.get('PATH','')}\n")

    def _emit(self, s: str) -> None:
        if s:
            self.log.emit(s)

    def _run_async(self, work: Callable[[], None]) -> None:
        self.pool.start(_Runnable(work))

    def _minipro_missing_msg(self) -> str:
        return (
            "minipro not found.\n\n"
            "Install minipro and make sure it is in PATH.\n"
            "Common locations:\n"
            "  /opt/homebrew/bin/minipro\n"
            "  /usr/local/bin/minipro\n\n"
            f"Resolved minipro_path='{self.minipro_path}'\n"
            f"PATH='{os.environ.get('PATH','')}'"
        )

    def _check_minipro_exists(self) -> bool:
        mp = self.minipro_path
        if (os.path.sep in mp or mp.startswith(".")) and not os.path.exists(mp):
            return False
        if mp == "minipro" and not shutil.which("minipro"):
            return False
        return True

    def reload(self) -> None:
        def work():
            try:
                if not self._check_minipro_exists():
                    self._emit(f"[reload] failed: {self._minipro_missing_msg()}\n")
                    self.programmerChanged.emit("Unknown")
                    return

                self._emit("[reload] probing programmer via TTY …\n")
                prog = self.loader.reload()
                self._emit(f"[detect] programmer: {prog}\n")
                self.programmerChanged.emit(prog)
            except Exception as e:
                self._emit(f"[reload] failed: {e}\n")
                self.programmerChanged.emit("Unknown")

        self._run_async(work)

    def set_chip(self, chip: str) -> None:
        chip = (chip or "").strip()
        self.current_chip = chip
        self.chipChanged.emit(chip)

        if chip:
            info = self.loader.get_info(chip)
            self._refresh_compact_info(info)
        else:
            self.last_chip_id = ""
            self.chipInfoChanged.emit("")

    def _refresh_compact_info(self, info: ChipInfo) -> None:
        lines: list[str] = [f"Device: {info.chip}"]

        if self.last_chip_id:
            lines.append(f"Chip ID: {self.last_chip_id}")

        def find_line(prefixes: list[str]) -> Optional[str]:
            for ln in (info.raw or "").splitlines():
                s = ln.strip()
                low = s.lower()
                for p in prefixes:
                    if low.startswith(p):
                        return s
            return None

        dev_code = find_line(["device code:"])
        mem = find_line(["memory:"])
        proto = find_line(["protocol:"])
        rbuf = find_line(["read buffer", "read buffer size"])
        wbuf = find_line(["write buffer", "write buffer size"])

        for item in [dev_code, mem, proto, rbuf, wbuf]:
            if item:
                lines.append(item)

        if len(lines) <= 1 and info.short:
            lines.append(info.short)

        self.chipInfoChanged.emit("\n".join(lines).strip())

    def auto_detect_chip(self) -> None:
        if self.current_chip:
            self.read_chip_id()
        else:
            self.spi_auto_detect()

    def read_chip_id(self) -> None:
        chip = self.current_chip
        if not chip:
            self.operationFinished.emit(False, "Select IC first (required for Read ID)")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit(f"[op] read id: minipro -p {chip} -D …\n")
            buf: list[str] = []

            def on_chunk(t: str):
                buf.append(t)
                self._emit(t)

            rc, out = run_tty_stream([self.minipro_path, "-p", chip, "-D"], timeout_sec=60.0, on_chunk=on_chunk)
            full = out if out else "".join(buf)

            if rc == 0:
                parsed = self._parse_id_from_output(full)
                self.last_chip_id = parsed or ""
                info = self.loader.get_info(chip)
                self._refresh_compact_info(info)
                self.operationFinished.emit(True, "Read ID finished" if self.last_chip_id else "Read ID finished (not parsed)")
            else:
                self.operationFinished.emit(False, f"Read ID failed (rc={rc})")

        self._run_async(work)

    def spi_auto_detect(self) -> None:
        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit("[op] spi auto-detect: minipro -a 8 …\n")
            rc1, out1 = run_tty_stream([self.minipro_path, "-a", "8"], timeout_sec=90.0, on_chunk=self._emit)
            dev = self._parse_device_from_autodetect(out1) if rc1 == 0 else ""

            if not dev:
                self._emit("\n[op] spi auto-detect: minipro -a 16 …\n")
                rc2, out2 = run_tty_stream([self.minipro_path, "-a", "16"], timeout_sec=90.0, on_chunk=self._emit)
                dev = self._parse_device_from_autodetect(out2) if rc2 == 0 else ""

            if dev:
                self._emit(f"\n[detect] SPI device: {dev}\n")
                self.last_chip_id = ""
                self.set_chip(dev)
                self.operationFinished.emit(True, f"Auto-detected SPI: {dev}")
            else:
                self._emit("\n[detect] SPI auto-detect found nothing.\n")
                self.operationFinished.emit(False, "Auto-detect: only SPI 25xx is supported by minipro (-a 8/16). Select IC manually.")

        self._run_async(work)

    @staticmethod
    def _parse_id_from_output(text: str) -> str:
        for ln in text.splitlines():
            s = ln.strip()
            low = s.lower()
            if "chip id" in low or re.search(r"\bid\b", low):
                if ":" in s:
                    return s.split(":", 1)[1].strip()
                return s

        m = re.search(r"(0x[0-9a-fA-F]+)", text)
        if m:
            return m.group(1)

        m2 = re.search(r"\b([0-9a-fA-F]{8,})\b", text)
        if m2:
            return m2.group(1)

        return ""

    @staticmethod
    def _parse_device_from_autodetect(text: str) -> str:
        m = re.search(r"([A-Za-z0-9][A-Za-z0-9_.+\-]*@[A-Za-z0-9][A-Za-z0-9_.+\-]*)", text)
        if m:
            return m.group(1).strip()

        m2 = re.search(r"(?im)^\s*(detected|found)\s*:\s*(.+?)\s*$", text)
        if m2:
            return m2.group(2).strip()

        return ""

    def read_to_tmp(self) -> None:
        chip = self.current_chip
        if not chip:
            self.operationFinished.emit(False, "No chip selected")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            tmp_dir = tempfile.gettempdir()
            out_path = os.path.join(tmp_dir, "dump.bin")
            self.last_dump_path = out_path

            self._emit(f"[op] read -> {out_path}\n")
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

            rc, _ = run_tty_stream(
                [self.minipro_path, "-p", chip, "-r", out_path],
                timeout_sec=600.0,
                on_chunk=self._emit,
            )
            ok = (rc == 0) and os.path.exists(out_path)
            self.operationFinished.emit(ok, "Read OK" if ok else f"Read failed (rc={rc})")

        self._run_async(work)

    def write_chip(self, in_path: str, opts: WriteOptions) -> None:
        chip = self.current_chip
        if not chip:
            self.operationFinished.emit(False, "No chip selected")
            return
        if not in_path or not os.path.exists(in_path):
            self.operationFinished.emit(False, "Input file does not exist")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit(f"[op] write: {in_path} -> {chip}\n")
            cmd = [self.minipro_path, "-p", chip, "-w", in_path]

            if not opts.erase_before_write:
                cmd.append("-e")

            if opts.skip_verification:
                cmd.append("-v")

            rc, _ = run_tty_stream(cmd, timeout_sec=1200.0, on_chunk=self._emit)
            ok = (rc == 0)
            self.operationFinished.emit(ok, "Write OK" if ok else f"Write failed (rc={rc})")

        self._run_async(work)

    def erase_chip(self) -> None:
        chip = self.current_chip
        if not chip:
            self.operationFinished.emit(False, "No chip selected")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit(f"[op] erase: {chip}\n")
            rc, _ = run_tty_stream([self.minipro_path, "-p", chip, "-E"], timeout_sec=600.0, on_chunk=self._emit)
            ok = (rc == 0)
            self.operationFinished.emit(ok, "Erase OK" if ok else f"Erase failed (rc={rc})")

        self._run_async(work)

    def blank_check(self) -> None:
        chip = self.current_chip
        if not chip:
            self.operationFinished.emit(False, "No chip selected")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit(f"[op] blank_check: {chip}\n")
            rc, _ = run_tty_stream([self.minipro_path, "-p", chip, "-b"], timeout_sec=600.0, on_chunk=self._emit)
            ok = (rc == 0)
            self.operationFinished.emit(ok, "Blank Check OK" if ok else f"Blank Check failed (rc={rc})")

        self._run_async(work)

    def update_firmware(self, update_dat_path: str) -> None:
        if not update_dat_path or not os.path.exists(update_dat_path):
            self.operationFinished.emit(False, "update.dat not found")
            return

        def work():
            if not self._check_minipro_exists():
                self.operationFinished.emit(False, self._minipro_missing_msg())
                return

            self._emit(f"[op] firmware update: {update_dat_path}\n")
            rc, _ = run_tty_stream([self.minipro_path, "-F", update_dat_path], timeout_sec=1200.0, on_chunk=self._emit)
            ok = (rc == 0)
            self.operationFinished.emit(ok, "Firmware update OK" if ok else f"Firmware update failed (rc={rc})")

        self._run_async(work)
