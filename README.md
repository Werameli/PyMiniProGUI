# PyMiniProGUI - GUI Wrapper for minipro-cli written in Python

<img width="1004" height="631" alt="CleanShot 2026-02-08 at 02 07 18" src="https://github.com/user-attachments/assets/0f0bf6fd-a6cf-4611-a8c4-18c97e07be5a" />

## About

A simple yet effective **GUI wrapper** for those who don’t like typing in the terminal.

Built on **PySide6**, with **minipro** as the backend, it supports the following programmers:

- T56  
- T48  
- T866II+  


This project was heavily inspired by **minipro-gui** (GUI Wrapper) by **twelve-chairs**:  
https://github.com/twelve-chairs/minipro-gui

At the moment, the original project is broken, so I decided to create an alternative.

PyMiniProGUI keeps a **similar interface and feature set**, but is:
- written in **Python**
- aimed at **fixing the problems** of the old wrapper

## Usage

You can use **PyMiniProGUI** in one of the following ways:

- Download a pre-built release (coming soon):
  - **AppImage** (Linux)
  - **.app** (macOS)

- Build it yourself using `build.sh` (requires **Docker**)

- Or just use as is, via launching app.py and downloading source code :)

> **Warning**  
> For now, the build system is not complete and in Beta stage of development so it works **only on Apple Silicon Macs**, due to the specifics of compiling Linux builds.

## Issues

Even though the wrapper is labeled **v1.0.0**, that doesn’t mean it’s fully complete.

I’m happy to review any issues related to the app. I’m also actively looking for:

- **x86-based Linux** users (for testing)
- **ARM-based Linux** users (for testing)
- **x86-based macOS** users (for releasing an x86 build for macOS)
- Owners of these programmers:
  - **T56**
  - **T866II+**

If you’d like to collaborate or report a bug — **open an issue**!


## Release Packages Status

### Tested
- macOS ARM build  
- Linux ARM build
- Linux x86-64 build







