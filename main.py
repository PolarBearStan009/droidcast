import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Droidcast')
    app.setApplicationDisplayName('Droidcast')
    app.setStyle('Fusion')

    from ui.theme import STYLESHEET
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
