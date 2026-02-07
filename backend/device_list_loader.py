from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .pty_runner import run_tty_stream


@dataclass
class ChipInfo:
    chip: str
    short: str = ""
    raw: str = ""


class DeviceListLoader:
    def __init__(self, minipro_path: str = "minipro"):
        self.minipro_path = minipro_path
        self.programmer: str = "Unknown"

        self._cache_prefix: Dict[str, List[str]] = {}
        self._cache_search: Dict[str, List[str]] = {}
        self._cache_info: Dict[str, ChipInfo] = {}
        self._prefixes_cached: Optional[List[str]] = None

    def reload(self) -> str:
        self._cache_prefix.clear()
        self._cache_search.clear()
        self._cache_info.clear()
        self._prefixes_cached = None

        rc, out = run_tty_stream([self.minipro_path, "-k"], timeout_sec=10.0)
        if rc != 0:
            self.programmer = "Unknown"
            raise RuntimeError("minipro -k failed")

        m = re.search(r"(?im)^\s*\w+\s*:\s*(T48|T56|TL866II\+|TL866A|TL866CS)\s*$", out)
        if m:
            self.programmer = m.group(1).strip()
        else:
            m2 = re.search(r"(?im)\bFound\s+(T48|T56|TL866II\+|TL866A|TL866CS)\b", out)
            self.programmer = m2.group(1).strip() if m2 else "Unknown"

        return self.programmer

    def compute_prefixes(self) -> List[str]:
        if self._prefixes_cached is not None:
            return self._prefixes_cached

        candidates = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_+-.")
        found: List[str] = []

        for ch in candidates:
            chips = self.list_by_prefix(ch)
            if chips:
                key = ch.upper() if ch.isalpha() else ch
                if key not in found:
                    found.append(key)

        digits = sorted([x for x in found if x.isdigit()])
        letters = sorted([x for x in found if x.isalpha()])
        other = sorted([x for x in found if not x.isalnum()])
        self._prefixes_cached = digits + letters + other
        return self._prefixes_cached

    def list_by_prefix(self, prefix: str) -> List[str]:
        p = (prefix or "").strip()
        if not p:
            return []
        p = p[0]

        key = p.upper() if p.isalpha() else p
        if key in self._cache_prefix:
            return self._cache_prefix[key]

        rc, out = run_tty_stream([self.minipro_path, "-L", p], timeout_sec=30.0)
        if rc != 0:
            self._cache_prefix[key] = []
            return []

        chips = self._parse_list_output(out)

        filtered: List[str] = []
        for token in chips:
            name = token.split("@", 1)[0]
            if not name:
                continue
            first = name[0]
            if p.isalpha():
                if first.upper() == p.upper():
                    filtered.append(token)
            else:
                if first == p:
                    filtered.append(token)

        filtered = sorted(set(filtered))
        self._cache_prefix[key] = filtered
        return filtered

    def search(self, query: str) -> List[str]:
        q = (query or "").strip()
        if not q:
            return []
        if q in self._cache_search:
            return self._cache_search[q]

        rc, out = run_tty_stream([self.minipro_path, "-L", q], timeout_sec=30.0)
        if rc != 0:
            self._cache_search[q] = []
            return []

        chips = sorted(set(self._parse_list_output(out)))
        self._cache_search[q] = chips
        return chips

    @staticmethod
    def _parse_list_output(text: str) -> List[str]:
        res: List[str] = []
        for ln in (text or "").splitlines():
            s = ln.strip()
            if not s:
                continue

            low = s.lower()
            if low.startswith("found ") or low.startswith("warning:") or low.startswith("minipro version"):
                continue
            if "usage:" in low:
                continue

            s = re.sub(r"\s*@\s*", "@", s)

            for m in re.finditer(r"\b([A-Za-z0-9][A-Za-z0-9_.+\-]*@[A-Za-z0-9][A-Za-z0-9_.+\-]*)\b", s):
                res.append(m.group(1))

        return res

    def get_info(self, chip: str) -> ChipInfo:
        chip = (chip or "").strip()
        if not chip:
            return ChipInfo(chip="")

        if chip in self._cache_info:
            return self._cache_info[chip]

        rc, out = run_tty_stream([self.minipro_path, "-d", chip], timeout_sec=20.0)
        raw = (out or "").strip()

        short_lines: List[str] = []
        keep_prefixes = (
            "device code:",
            "memory:",
            "package:",
            "protocol:",
            "read buffer",
            "write buffer",
        )
        for ln in raw.splitlines():
            t = ln.strip()
            if not t:
                continue
            low = t.lower()
            if low.startswith("found ") or low.startswith("warning:") or low.startswith("minipro version"):
                continue
            if "usage:" in low:
                continue
            if low.startswith(keep_prefixes):
                short_lines.append(t)

        info = ChipInfo(chip=chip, short="\n".join(short_lines).strip(), raw=raw)
        self._cache_info[chip] = info
        return info
