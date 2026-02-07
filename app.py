import os
import sys

from PySide6.QtWidgets import QApplication
from ui.strings import S
from ui.main_window import MainWindow

def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName(S.APP_NAME)
    app.setApplicationVersion(S.APP_VERSION)

    w = MainWindow()
    w.setFixedSize(1000, 600)
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
