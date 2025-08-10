import os
from PyQt5.QtCore import QThread, pyqtSignal
from .models import LogRow
from .parsing import parse_log_file, extract_log_info

class LogParseWorker(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)      # all_rows

    def __init__(self, log_files, show_simulate, show_compile, show_scoreboard, patterns, ignore_patterns=None, logger=None):
        super().__init__()
        self.log_files = log_files
        self.show_simulate = show_simulate
        self.show_compile = show_compile
        self.show_scoreboard = show_scoreboard
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns
        self.logger = logger
        self.ignore_patterns = ignore_patterns
        self._stop_requested = False
        self.memory_warning_threshold_mb = 1024  # You can make this configurable via a settings dialog
        self.log_files = log_files
        self.show_simulate = show_simulate
        self.show_compile = show_compile
        self.show_scoreboard = show_scoreboard
        self.patterns = patterns

    def run(self):
        all_rows = []
        for idx, filepath in enumerate(self.log_files):
            if self._stop_requested:
                break
            self.logger.info(f"Processing file {idx+1}/{len(self.log_files)}: {filepath}")
            id_val, testcase, testopt = extract_log_info(filepath)
            error_counts, fatal_counts, warning_counts = parse_log_file(
                filepath, self.patterns, self.ignore_patterns, logger=self.logger
            )

            for (msg_clean, msg_orig, lineno), count in error_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg_clean.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="ERROR",
                    count=count,
                    message=msg_clean,
                    orig_message=msg_orig,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)

            for (msg_clean, msg_orig, lineno), count in fatal_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg_clean.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="FATAL",
                    count=count,
                    message=msg_clean,
                    orig_message=msg_orig,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)

            for (msg_clean, msg_orig, lineno), count in warning_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg_clean.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="WARNING",
                    count=count,
                    message=msg_clean,
                    orig_message=msg_orig,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)
            self.progress.emit(idx+1, len(self.log_files))
        self.finished.emit(all_rows)

    def stop(self):
        self._stop_requested = True

