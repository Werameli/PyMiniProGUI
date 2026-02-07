from __future__ import annotations


class S:
    APP_VERSION = "1.0.0"
    APP_DEVELOPER = "Werameli"
    APP_NAME = f"PyMiniProGUI {APP_VERSION} by {APP_DEVELOPER}"
    APP_WEBSITE = "https://github.com/your/repo"
    BACKEND_VERSION = "0.7.4"
    BACKEND_NAME = f"minipro {BACKEND_VERSION}"

    ABOUT_TITLE = "About"
    ABOUT_TEXT = (
        "PyMiniProGUI — GUI Application based on minipro-cli for XGecu Programmers.\n"
        "Inspired by twelve-chairs' minipro-gui (Available at GitHub).\n"
        "App logo by twelve-chairs\n\n"
        "• GUI: PySide6\n"
        f"• Backend (Last tested with): {BACKEND_NAME}\n\n"
        "Disclaimer:\n"
        "This project is not affiliated with XGecu.\n"
        "It's completely free. If you paid for this software - you've been scammed!\n\n"
        "Official PyMiniProGUI Website: https://github.com/werameli/pyminiprogui"
    )

    GB_TARGETS = "Targets"
    GB_DEVICE_INFO = "Device Info"
    GB_OPERATIONS = "Operations"
    GB_OUTPUT = "Output"
    GB_HEX = "Hex View"

    LBL_PROGRAMMER_PREFIX = "Programmer:"
    BTN_RELOAD = "Reload"
    BTN_UPGRADE_FW = "Upgrade Firmware"
    BTN_ABOUT = "About"

    BTN_AUTO_DETECT = "Auto Detect / Read ID"
    BTN_SELECT_IC = "Select IC"

    DI_DEVICE = "Device:"
    DI_MEMORY = "Memory:"
    DI_PACKAGE = "Package:"
    DI_PROTOCOL = "Protocol:"
    DI_READ_BUF = "Read Buffer:"
    DI_WRITE_BUF = "Write Buffer:"

    CB_IGNORE_ID = "Ignore ID Error"
    CB_IGNORE_SIZE = "Ignore Size Error"
    CB_SKIP_ID = "Skip ID Check"
    CB_SKIP_VERIFY = "Skip Verify"

    BTN_READ = "Read From Device"
    BTN_WRITE = "Write to Device"
    BTN_SAVE_DUMP = "Save dump"
    BTN_PIN = "Pin Check"
    BTN_BLANK = "Blank Check"
    BTN_ERASE = "Erase Device"
    BTN_HW = "Hardware Check"
