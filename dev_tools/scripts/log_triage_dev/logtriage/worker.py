from PyQt5.QtCore import QThread, pyqtSignal
from .parsing import parse_log_file, extract_log_info

class LogParseWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)

    def __init__(self, log_files, show_simulate, show_compile, show_scoreboard):
        super().__init__()
        self.log_files = log_files
        self.show_simulate = show_simulate
        self.show_compile = show_compile
        self.show_scoreboard = show_scoreboard

    def run(self):
        all_rows = []
        for idx, filepath in enumerate(self.log_files):
            id_val, testcase, testopt = extract_log_info(filepath)
            error_counts, fatal_counts, warning_counts = parse_log_file(filepath)
            for msg, count in error_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = [
                    id_val, testcase, testopt, "ERROR", count, msg, "simulate" if "simulate" in filepath else "compile", filepath
                ]
                all_rows.append(row)
            for msg, count in fatal_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = [
                    id_val, testcase, testopt, "FATAL", count, msg, "simulate" if "simulate" in filepath else "compile", filepath
                ]
                all_rows.append(row)
            for msg, count in warning_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = [
                    id_val, testcase, testopt, "WARNING", count, msg, "simulate" if "simulate" in filepath else "compile", filepath
                ]
                all_rows.append(row)
            self.progress.emit(idx+1, len(self.log_files))
        self.finished.emit(all_rows)