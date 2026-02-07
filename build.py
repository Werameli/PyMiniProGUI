from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from ui.strings import S

# -----------------------------------------------------------------------------
# Linux build settings (via env vars)
# -----------------------------------------------------------------------------
PYTHON_VERSION = os.environ.get("PYTHON_VERSION", "3.10").strip()
DOCKER_IMAGE = os.environ.get("DOCKER_IMAGE", f"python:{PYTHON_VERSION}-bookworm").strip()
LINUX_PY = os.environ.get("LINUX_PY", "python").strip()

# Packaging mode:
#   appimage (default) -> dist/appimage-{arch}/*.AppImage
#   dir               -> dist/linux-{arch}/{AppName}/ (PyInstaller onedir folder)
LINUX_PACKAGE = os.environ.get("LINUX_PACKAGE", "appimage").strip().lower()
if LINUX_PACKAGE not in {"appimage", "dir"}:
    raise SystemExit("LINUX_PACKAGE must be 'appimage' or 'dir'")

# Which Linux arches to build:
#   LINUX_ARCHES=arm64 python3 build.py
#   LINUX_ARCHES=x86_64,arm64 python3 build.py
LINUX_ARCHES = [a.strip() for a in os.environ.get("LINUX_ARCHES", "x86_64,arm64").split(",") if a.strip()]
for a in LINUX_ARCHES:
    if a not in {"x86_64", "arm64"}:
        raise SystemExit("LINUX_ARCHES must be a comma list of: x86_64,arm64")

# Extra deps bundling (ldd scan) - can be slow under emulation
#   BUNDLE_DEPS=0 (default) -> skip
#   BUNDLE_DEPS=1           -> limited ldd scan with per-file timeout
BUNDLE_DEPS_DEFAULT = os.environ.get("BUNDLE_DEPS", "0").strip()

# SquashFS compression used inside AppImage type2 runtime.
# type2-runtime supports zstd and zlib (use 'gzip' for zlib-compatible squashfs).
#   SQUASH_COMP=zstd (default) or SQUASH_COMP=gzip
SQUASH_COMP = os.environ.get("SQUASH_COMP", "zstd").strip().lower()
if SQUASH_COMP in {"zlib", "gzip"}:
    SQUASH_COMP_MKSQUASHFS = "gzip"
elif SQUASH_COMP == "zstd":
    SQUASH_COMP_MKSQUASHFS = "zstd"
else:
    raise SystemExit("SQUASH_COMP must be zstd or gzip (or zlib)")

# Type2 runtime URLs (we DO NOT execute them; we just prepend to squashfs)
RUNTIME_URL_X86_64 = os.environ.get(
    "RUNTIME_URL_X86_64",
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64",
).strip()
RUNTIME_URL_AARCH64 = os.environ.get(
    "RUNTIME_URL_AARCH64",
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-aarch64",
).strip()


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n>>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def run_capture(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def docker_exists() -> bool:
    return shutil.which("docker") is not None


def norm_name() -> str:
    # stable internal name used for binaries / desktop file / icon name
    return S.APP_NAME.replace("(", "").replace(")", "").replace(" ", "")


def icon_macos(root: Path) -> str | None:
    p = root / "assets" / "icon.icns"
    return str(p) if p.exists() else None


def icon_linux(root: Path) -> str | None:
    p = root / "assets" / "icon.png"
    return str(p) if p.exists() else None


def make_datas(root: Path) -> list[tuple[Path, str]]:
    datas: list[tuple[Path, str]] = []

    ui_assets = root / "ui" / "assets"
    if ui_assets.exists():
        datas.append((ui_assets, "ui/assets"))

    proj_assets = root / "assets"
    if proj_assets.exists():
        datas.append((proj_assets, "assets"))

    return datas


def preflight_docker_platform(docker_platform: str) -> None:
    rc, out = run_capture(["docker", "run", "--rm", "--platform", docker_platform, DOCKER_IMAGE, "uname", "-m"])
    if rc == 0:
        print(f"[build] docker platform ok: {docker_platform} -> {out.strip()}")
        return

    print(out)
    low = out.lower()
    if "tls:" in low or "x509" in low or "certificate" in low or "proxy" in low:
        print(
            "\n[build] Looks like a network/proxy/TLS issue while pulling/running Docker images.\n"
            f"Try: docker pull {DOCKER_IMAGE}\n"
        )
        raise SystemExit(2)

    if "exec format error" in low or "qemu" in low or "rosetta" in low:
        print(
            "\n[build] Multi-arch emulation looks disabled.\n"
            "On macOS Apple Silicon: enable amd64/x86_64 emulation (Rosetta/QEMU) in Docker Desktop, then restart.\n"
        )
        raise SystemExit(2)

    print(
        "\n[build] Docker failed to run the preflight container.\n"
        f"Try manually:\n  docker run --rm --platform {docker_platform} {DOCKER_IMAGE} uname -m\n"
    )
    raise SystemExit(2)


# ---------------- macOS (ARM only) local build ----------------

def build_macos_arm(root: Path, entry: Path) -> None:
    sysname = platform.system().lower()
    if sysname != "darwin":
        print("[build] macOS build skipped (not macOS host).")
        return

    name_base = norm_name()
    dist_dir = root / "dist" / "macos-arm64"
    build_dir = root / "build" / "macos-arm64"
    dist_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    icon = icon_macos(root)
    if not icon:
        print("[build] warning: assets/icon.icns not found (macOS app without icon).")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", f"{name_base}-arm64",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--noconsole",
        "--target-architecture", "arm64",
        "--collect-all", "PySide6",
        "--hidden-import", "PySide6.QtSvg",
        "--hidden-import", "PySide6.QtXml",
    ]

    if icon:
        cmd += ["--icon", icon]

    for host_path, target in make_datas(root):
        cmd += ["--add-data", f"{host_path}{os.pathsep}{target}"]

    cmd.append(str(entry))

    print("\n[build] macOS ARM-only (.app)")
    run(cmd, cwd=root)
    print(f"[build] macOS output: {dist_dir}")


# ---------------- Linux via Docker: PyInstaller + AppImage (manual runtime+squashfs) ----------------

def build_linux_via_docker(root: Path, entry: Path) -> None:
    if not docker_exists():
        raise SystemExit("Docker not found. Install Docker Desktop and ensure `docker` is in PATH.")

    app_name = norm_name()
    icon = icon_linux(root)
    if not icon:
        print("[build] warning: assets/icon.png not found. AppImage will be built, but may have no icon.")

    datas = make_datas(root)
    req = root / "requirements.txt"
    has_req = req.exists()

    def docker_build_for(arch: str, docker_platform: str) -> None:
        preflight_docker_platform(docker_platform)

        dist_dir = root / "dist" / f"linux-{arch}"
        build_dir = root / "build" / f"linux-{arch}"
        out_dir = root / "dist" / f"appimage-{arch}"
        dist_dir.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        add_data_args: list[str] = []
        for host_path, target in datas:
            rel = host_path.relative_to(root)
            add_data_args += ["--add-data", f"/work/{rel}:{target}"]

        icon_args: list[str] = []
        if (root / "assets" / "icon.png").exists():
            icon_args = ["--icon", "/work/assets/icon.png"]

        req_install = (
            f"{LINUX_PY} -m pip install -r /work/requirements.txt"
            if has_req
            else f"{LINUX_PY} -m pip install PySide6"
        )

        pi_cmd = [
            LINUX_PY, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--name", app_name,
            "--distpath", f"/work/dist/linux-{arch}",
            "--workpath", f"/work/build/linux-{arch}",
            "--noconsole",
            "--collect-all", "PySide6",
            "--hidden-import", "PySide6.QtSvg",
            "--hidden-import", "PySide6.QtXml",
            *icon_args,
            *add_data_args,
            "/work/app.py",
        ]

        if arch == "x86_64":
            expected_uname = "x86_64"
            runtime_url = RUNTIME_URL_X86_64
        else:
            expected_uname = "aarch64"
            runtime_url = RUNTIME_URL_AARCH64

        sh = f"""
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[container] image: {DOCKER_IMAGE}"
{LINUX_PY} -V
echo "[container] uname -m: $(uname -m)"

U="$(uname -m)"
if [ "$U" != "{expected_uname}" ]; then
  echo ""
  echo "[ERROR] Container architecture is '$U' but target is '{arch}' (expected '{expected_uname}')."
  echo "Enable amd64/x86_64 emulation in Docker Desktop (Rosetta/QEMU) and restart Docker Desktop."
  echo ""
  exit 126
fi

# System deps:
# - squashfs-tools: mksquashfs for manual AppImage creation
# - patchelf + typical Qt runtime deps (helps runtime)
apt-get update
apt-get install -y --no-install-recommends \\
  build-essential patchelf \\
  curl ca-certificates file \\
  squashfs-tools \\
  libgl1 libxkbcommon0 libxkbcommon-x11-0 \\
  libx11-6 libxext6 libxrender1 libxrandr2 libxi6 \\
  libxcb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \\
  libdbus-1-3 libfontconfig1 libfreetype6 \\
  libglib2.0-0 libnss3 libxss1 \\
  tzdata
rm -rf /var/lib/apt/lists/*

# Python deps
{LINUX_PY} -m pip install -U pip wheel setuptools
{req_install}
{LINUX_PY} -m pip install -U pyinstaller

echo "[container] running PyInstaller..."
{" ".join(pi_cmd)}

echo "[container] PyInstaller output: /work/dist/linux-{arch}/{app_name}/"
ls -la "/work/dist/linux-{arch}/{app_name}" || true

if [ "{LINUX_PACKAGE}" != "appimage" ]; then
  echo "[container] LINUX_PACKAGE=dir -> skip AppImage packaging"
  exit 0
fi

echo "[container] building AppImage manually (runtime + squashfs)..."

APPDIR="/work/build/linux-{arch}/AppDir"
OUTDIR="/work/dist/appimage-{arch}"
BUNDLE_DIR="$APPDIR/usr/lib/{app_name}"

rm -rf "$APPDIR"
mkdir -p "$BUNDLE_DIR" "$OUTDIR"

# Copy PyInstaller onedir into AppDir
cp -a "/work/dist/linux-{arch}/{app_name}/." "$BUNDLE_DIR/"

# Optional: limited deps bundling (can help on very minimal distros)
BUNDLE_DEPS="{BUNDLE_DEPS_DEFAULT}"
DEPS_DIR="$BUNDLE_DIR/deps"
mkdir -p "$DEPS_DIR"

if [ "$BUNDLE_DEPS" = "1" ]; then
  echo "[container] BUNDLE_DEPS=1 -> limited ldd scan (timeout per file)"
  apt-get update
  apt-get install -y --no-install-recommends coreutils
  rm -rf /var/lib/apt/lists/*

  is_elf() {{ file -b "$1" 2>/dev/null | grep -q '^ELF'; }}

  should_skip_lib() {{
    case "$1" in
      /lib/*/ld-linux*.so*|/lib64/ld-linux*.so*|/lib/*/libc.so.*|/lib/*/libm.so.*|/lib/*/libdl.so.*|/lib/*/libpthread.so.*|/lib/*/librt.so.*)
        return 0 ;;
      *) return 1 ;;
    esac
  }}

  collect_one() {{
    f="$1"
    timeout 5s ldd "$f" 2>/dev/null \\
      | awk '{{for(i=1;i<=NF;i++){{ if($i ~ /^\\//) print $i; if($i=="=>") print $(i+1); }}}}' \\
      | grep '^/' | sed 's/,$//' | sort -u
  }}

  TARGETS=""
  [ -f "$BUNDLE_DIR/{app_name}" ] && TARGETS="$TARGETS $BUNDLE_DIR/{app_name}"
  if [ -d "$BUNDLE_DIR/_internal" ]; then
    TARGETS="$TARGETS $(find "$BUNDLE_DIR/_internal" -maxdepth 1 -type f -name "*.so*" | head -n 120)"
  fi

  n=0
  for f in $TARGETS; do
    is_elf "$f" || continue
    n=$((n+1))
    [ $((n % 20)) -eq 0 ] && echo "[container] deps scan progress: $n files..."
    for d in $(collect_one "$f"); do
      [ -f "$d" ] || continue
      should_skip_lib "$d" && continue
      bn="$(basename "$d")"
      [ -f "$DEPS_DIR/$bn" ] || cp -L "$d" "$DEPS_DIR/$bn" || true
    done
  done
  echo "[container] deps bundled: $(ls -1 "$DEPS_DIR" 2>/dev/null | wc -l)"
else
  echo "[container] BUNDLE_DEPS=$BUNDLE_DEPS -> skip deps scan"
fi

# AppRun at AppDir root (required by runtime)
cat > "$APPDIR/AppRun" << EOF
#!/bin/sh
set -e
APPDIR="\$(dirname "\$(readlink -f "\$0")")"
APPNAME="{app_name}"
BUNDLE="\$APPDIR/usr/lib/\$APPNAME"

LDLP="\$BUNDLE:\$BUNDLE/_internal:\$BUNDLE/PySide6/Qt/lib:\$BUNDLE/deps"
if [ -n "\$LD_LIBRARY_PATH" ]; then
  export LD_LIBRARY_PATH="\$LDLP:\$LD_LIBRARY_PATH"
else
  export LD_LIBRARY_PATH="\$LDLP"
fi

if [ -d "\$BUNDLE/PySide6/Qt/plugins" ]; then
  export QT_PLUGIN_PATH="\$BUNDLE/PySide6/Qt/plugins"
  export QT_QPA_PLATFORM_PLUGIN_PATH="\$BUNDLE/PySide6/Qt/plugins/platforms"
fi
if [ -d "\$BUNDLE/PySide6/Qt/qml" ]; then
  export QML2_IMPORT_PATH="\$BUNDLE/PySide6/Qt/qml"
fi

if [ -n "\$XDG_DATA_DIRS" ]; then
  export XDG_DATA_DIRS="\$APPDIR/usr/share:\$XDG_DATA_DIRS"
else
  export XDG_DATA_DIRS="\$APPDIR/usr/share:/usr/local/share:/usr/share"
fi

exec "\$BUNDLE/{app_name}" "\$@"
EOF
chmod +x "$APPDIR/AppRun"

# Desktop file at AppDir root
cat > "$APPDIR/{app_name}.desktop" << EOF
[Desktop Entry]
Type=Application
Name={S.APP_NAME}
Exec=AppRun
Icon={app_name}
Categories=Utility;
Terminal=false
EOF

# Icon at AppDir root (recommended)
if [ -f "/work/assets/icon.png" ]; then
  cp "/work/assets/icon.png" "$APPDIR/{app_name}.png"
fi

# Build squashfs of AppDir
SQUASH="/work/build/linux-{arch}/{app_name}.squashfs"
rm -f "$SQUASH"
mksquashfs "$APPDIR" "$SQUASH" -noappend -comp {SQUASH_COMP_MKSQUASHFS} -b 131072 >/work/build/linux-{arch}/mksquashfs.log 2>&1 || {{
  echo "[ERROR] mksquashfs failed; tail log:"
  tail -n 80 /work/build/linux-{arch}/mksquashfs.log || true
  exit 1
}}

# Download runtime (we DO NOT execute it) and concatenate
RUNTIME="/work/build/linux-{arch}/runtime"
curl -L -o "$RUNTIME" "{runtime_url}"
chmod +x "$RUNTIME"
file "$RUNTIME" || true

OUT="$OUTDIR/{app_name}-{arch}.AppImage"
rm -f "$OUT"
cat "$RUNTIME" "$SQUASH" > "$OUT"
chmod +x "$OUT"

echo ""
echo "[container] done:"
echo "  AppImage: $OUT"
ls -la "$OUTDIR" || true
"""

        cmd = [
            "docker", "run", "--rm",
            "--platform", docker_platform,
            "-v", f"{root}:/work",
            "-w", "/work",
            DOCKER_IMAGE,
            "bash", "-lc", sh.strip(),
        ]

        print(f"\n[build] Linux {arch} via docker ({docker_platform}) | Python {PYTHON_VERSION} | package={LINUX_PACKAGE}")
        run(cmd, cwd=root)

    if "x86_64" in LINUX_ARCHES:
        docker_build_for("x86_64", "linux/amd64")
    if "arm64" in LINUX_ARCHES:
        docker_build_for("arm64", "linux/arm64")


def main() -> None:
    root = Path(__file__).resolve().parent
    entry = root / "app.py"
    if not entry.exists():
        raise SystemExit(f"Entry not found: {entry}")

    print(f"[build] target: Linux via Docker ({DOCKER_IMAGE}), package={LINUX_PACKAGE}, arches={','.join(LINUX_ARCHES)}")
    build_linux_via_docker(root, entry)

    print("\n[build] target: macOS ARM-only (.app) (local)")
    build_macos_arm(root, entry)

    print("\n[build] done. Check dist/ folder.")


if __name__ == "__main__":
    main()