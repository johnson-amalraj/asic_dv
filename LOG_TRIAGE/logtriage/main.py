import sys
from PyQt5.QtWidgets import QApplication
from .main_window import LogTriageWindow
from .utils import set_light_palette, setup_logging

if __name__ == "__main__":
    logger = setup_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    set_light_palette(app)
    win = LogTriageWindow(logger)  # Pass logger here
    win.show()
    sys.exit(app.exec_())

