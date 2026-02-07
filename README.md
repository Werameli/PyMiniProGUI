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

- Download a pre-built release:
  - **AppImage** (Linux)
  - **.app** (macOS)

- Build it yourself using `build.sh` (requires **Docker**)

> **Warning**  
> For now, the build system works **only on Apple Silicon Macs**, due to the specifics of compiling Linux builds.

## Release Packages Status

### Tested
- macOS ARM build  
- Linux ARM build *(AppImage)*  

### Untested
- Linux ARM build *(Native)*  
- Linux x86-64 build  
