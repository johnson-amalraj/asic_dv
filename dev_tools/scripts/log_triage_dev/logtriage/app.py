import sys
import logging
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from .mainwindow import LogTriageWindow

def log_uncaught_exceptions(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.error("Uncaught exception:\n%s", error_msg)
    QMessageBox.critical(None, "Unexpected Error",
        "An unexpected error occurred:\n\n" + str(value) +
        "\n\nSee tool_error.log for details.")

def main():
    logging.basicConfig(
        filename='tool_error.log',
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    sys.excepthook = log_uncaught_exceptions
    app = QApplication(sys.argv)
    win = LogTriageWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()