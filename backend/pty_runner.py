from __future__ import annotations

import os
import pty
import select
import subprocess
import time
from typing import Callable, List, Tuple, Optional


class PtyTimeoutError(RuntimeError):
    pass


def run_tty_stream(
    cmd: List[str],
    timeout_sec: float = 60.0,
    cwd: str | None = None,
    on_chunk: Optional[Callable[[str], None]] = None,
) -> Tuple[int, str]:
    master_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env.setdefault("TERM", "dumb")
    env.setdefault("LC_ALL", "C")

    p = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=cwd,
        env=env,
        close_fds=True,
        text=False,
    )
    os.close(slave_fd)

    out = bytearray()
    start = time.time()

    try:
        while True:
            if p.poll() is not None:
                while True:
                    r, _, _ = select.select([master_fd], [], [], 0.05)
                    if not r:
                        break
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    out.extend(chunk)
                    if on_chunk:
                        on_chunk(chunk.decode(errors="replace"))
                break

            if (time.time() - start) > timeout_sec:
                p.kill()
                raise PtyTimeoutError(f"PTY command timeout: {' '.join(cmd)}")

            r, _, _ = select.select([master_fd], [], [], 0.1)
            if r:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if chunk:
                    out.extend(chunk)
                    if on_chunk:
                        on_chunk(chunk.decode(errors="replace"))
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

    full = out.decode(errors="replace")
    return p.returncode or 0, full


def run_tty(cmd: List[str], timeout_sec: float = 60.0, cwd: str | None = None) -> Tuple[int, str]:
    return run_tty_stream(cmd, timeout_sec=timeout_sec, cwd=cwd, on_chunk=None)
