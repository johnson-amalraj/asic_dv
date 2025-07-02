import sys
import os
import csv
import gzip
import re
import logging
import traceback
import psutil
import matplotlib
import matplotlib.style

from collections import Counter, defaultdict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, 
    QWidget, QHBoxLayout, QLineEdit, QLabel, QProgressBar, QMenuBar, QMenu, QAction, 
    QMessageBox, QAbstractItemView, QHeaderView, QStatusBar, QDialog, QPushButton, 
    QInputDialog, QMenu, QTextEdit, QCheckBox, QComboBox
)

from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QSize
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from dataclasses import dataclass
from functools import partial

@dataclass
class LogRow:
    id: str
    testcase: str
    testopt: str
    type: str 
    count: int
    message: str
    logtype: str
    logfilepath: str
    linenumber: int

matplotlib.use('Qt5Agg')

MAX_RECENT_FOLDERS = 5
ROW_KEY_LEN = 8

RECENT_FOLDERS_KEY = "recentFolders"
EXCLUSION_LIST_KEY = "exclusionList"
LAST_FOLDER_KEY = "lastFolder"
COL_WIDTHS_KEY = "colWidths"
WIN_SIZE_KEY = "winSize"
WIN_POS_KEY = "winPos"

def parse_count_filter(expr, value):
    try:
        value = int(value)
    except Exception:
        return False
    expr = expr.strip()
    if not expr:
        return True
    if expr.startswith(">="):
        return value >= int(expr[2:])
    elif expr.startswith("<="):
        return value <= int(expr[2:])
    elif expr.startswith(">"):
        return value > int(expr[1:])
    elif expr.startswith("<"):
        return value < int(expr[1:])
    elif "-" in expr:
        parts = expr.split("-")
        return int(parts[0]) <= value <= int(parts[1])
    elif expr.startswith("=="):
        return value == int(expr[2:])
    else:
        return value == int(expr)

def clean_message(msg):
    msg = re.sub(r'@\s*\d+:?', '', msg)
    msg = re.sub(r'Actual clock period\s*:\s*\d+\.\d+', 'Actual clock period', msg)
    msg = re.sub(r'Actual Fifo Data\s*:\s*[0-9a-fA-Fx]+', 'Actual Fifo Data', msg)
    msg = re.sub(r'Expected Fifo Data\s*:\s*[0-9a-fA-Fx]+', 'Expected Fifo Data', msg)
    msg = re.sub(r'0x[0-9a-fA-F]+', '0xVAL', msg)
    msg = re.sub(r'\b\d+\b', 'N', msg)
    msg = re.sub(r'\s+', ' ', msg).strip()
    return msg

def open_log_file_anytype(filepath):
    if filepath.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
    else:
        return open(filepath, 'r', encoding='utf-8', errors='ignore')

def load_patterns_from_file(patterns_file):
    import csv
    patterns = []
    with open(patterns_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            typ = row['Type']
            regex = re.compile(row['Regex'])
            patterns.append((typ, regex))
    return patterns

def parse_log_file(filepath, patterns):
    logger.info(f"Start parsing: {filepath}")
    errors, fatals, warnings = [], [], []
    with open_log_file_anytype(filepath) as f:
        for lineno, line in enumerate(f, 1):
            # process line
            if lineno % 10000 == 0:
                # emit progress signal or update status bar
                logger.info(f"Processed {lineno} lines in {filepath}")
            line_stripped = line.strip()
            for typ, pat in patterns:
                m = pat.search(line_stripped)
                if m:
                    # Remove the matched prefix (from start of line up to and including the match)
                    start, end = m.span()
                    if start == 0:
                        msg = line_stripped[end:].lstrip(": \t")
                    else:
                        msg = line_stripped
                    msg = clean_message(msg)
                    if is_uvm_summary_line(line_stripped):
                        break
                    if typ == 'ERROR':
                        errors.append((msg, lineno))
                    elif typ == 'WARNING':
                        warnings.append((msg, lineno))
                    elif typ == 'FATAL':
                        fatals.append((msg, lineno))
                    break

    error_counts = Counter(errors)
    fatal_counts = Counter(fatals)
    warning_counts = Counter(warnings)
    logger.info(f"Finished parsing: {filepath}")
    return error_counts, fatal_counts, warning_counts

def is_uvm_summary_line(line):
    # Remove leading/trailing spaces for robust matching
    line = line.strip()
    return (
        re.match(r"Number of (demoted|caught) UVM_(FATAL|ERROR|WARNING) reports\s*:\s*\d+", line)
        is not None
    )

def extract_log_info(filepath):
    """
    Extracts (ID, testcase, testopt) from the log file path.
    """
    m = re.search(r'/max/([^/]+)', filepath)
    if m:
        name = m.group(1)
    else:
        # fallback: use the parent directory name
        name = os.path.basename(os.path.dirname(filepath))
    parts = name.split('-')
    testcase = parts[0] if len(parts) > 0 else ""
    testopt = parts[1] if len(parts) > 1 else ""
    id_val = ""
    for p in parts:
        if p.startswith("ID"):
            id_val = p[2:] if len(p) > 2 else ""
            break
    return (id_val, testcase, testopt)

def group_rows(rows):
    # Group by (Test Case, Test Option, Type, Message, Log Type)
    grouped = {}
    for row in rows:
        key = (row.testcase, row.testopt, row.type, row.message, row.logtype)
        if key not in grouped:
            grouped[key] = {
                "id": row.id,
                "testcase": row.testcase,
                "testopt": row.testopt,
                "type": row.type,
                "count": 0,
                "message": row.message,
                "logtype": row.logtype,
                "logfilepath": row.logfilepath,
                "linenumber": row.linenumber
            }
        grouped[key]["count"] += int(row.count)
    # Convert back to LogRow objects
    return [LogRow(**v) for v in grouped.values()]

def get_memory_usage_mb():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)
    return mem

class ChartDialog(QDialog):
    def __init__(self, fig, title="Chart", parent=None, filter_widgets=None, on_filter_change=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)
        if filter_widgets:
            filter_layout = QHBoxLayout()
            for widget in filter_widgets:
                filter_layout.addWidget(widget)
                if on_filter_change:
                    widget.currentIndexChanged.connect(on_filter_change)
            layout.addLayout(filter_layout)
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export as Image", self)
        export_btn.clicked.connect(self.export_image)
        btn_layout.addWidget(export_btn)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def export_image(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "Export Chart as Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
        if path:
            try:
                self.canvas.figure.savefig(path)
                QMessageBox.information(self, "Export", f"Chart exported to {path}")
                logger.info(f"Chart exported to {path}.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export chart:\n{e}")
                logger.error(f"Export Error", f"Failed to export chart:{e}")

class VisualizationDialog(QDialog):
    def __init__(self, parent, get_chart_data, dark_mode_enabled):
        super().__init__(parent)
        self.setWindowTitle("Visualization")
        self.resize(900, 600)
        self.get_chart_data = get_chart_data
        self.dark_mode_enabled = dark_mode_enabled

        # Chart type selector
        self.chart_combo = QComboBox(self)
        self.chart_combo.addItems(["Pie Chart", "Grouped Bar Chart", "Heatmap"])
        self.chart_combo.currentIndexChanged.connect(self.update_chart)

        # Chart area
        self.fig = Figure(figsize=(8, 6), facecolor=('#232629' if dark_mode_enabled else 'white'))
        self.canvas = FigureCanvas(self.fig)

        # Export and close buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export as Image", self)
        export_btn.clicked.connect(self.export_image)
        btn_layout.addWidget(export_btn)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.chart_combo)
        layout.addWidget(self.canvas)
        layout.addLayout(btn_layout)

        # Set dark mode for Matplotlib
        self.set_matplotlib_style(dark_mode_enabled)

        # Draw initial chart
        self.update_chart()

        # Set dialog background for dark mode
        if dark_mode_enabled:
            self.setStyleSheet("background-color: #232629; color: #F0F0F0;")

    def set_matplotlib_style(self, dark):
        import matplotlib
        matplotlib.style.use('dark_background' if dark else 'default')

    def update_chart(self):
        chart_type = self.chart_combo.currentText()
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        if chart_type == "Pie Chart":
            self.plot_pie(ax)
        elif chart_type == "Grouped Bar Chart":
            self.plot_bar(ax)
        elif chart_type == "Heatmap":
            self.plot_heatmap(ax)
        self.canvas.draw()

    def plot_pie(self, ax):
        stats, _ = self.get_chart_data()
        labels = []
        sizes = []
        colors = ['#e74c3c', '#8e44ad', '#f1c40f']
        for i, typ in enumerate(["ERROR", "FATAL", "WARNING"]):
            if stats[typ] > 0:
                labels.append(f"{typ} ({stats[typ]})")
                sizes.append(stats[typ])
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors[:len(sizes)])
            ax.set_title("Distribution of Error Types")
        else:
            ax.text(0.5, 0.5, "No data", ha='center', va='center')

    def plot_bar(self, ax):
        _, bar_data = self.get_chart_data()
        testcases, data = bar_data['testcases'], bar_data['data']
        types = ["ERROR", "FATAL", "WARNING"]
        x = range(len(testcases))
        width = 0.25
        colors = ['#e74c3c', '#8e44ad', '#f1c40f']
        for i, typ in enumerate(types):
            ax.bar([xi + i*width - width for xi in x], [data[tc][typ] for tc in testcases], width, label=typ, color=colors[i])
        ax.set_xticks(x)
        ax.set_xticklabels(testcases, rotation=45, ha='right')
        ax.set_ylabel("Count")
        ax.set_xlabel("Test Case")
        ax.set_title("Error/Fatal/Warning Counts by Test Case")
        ax.legend()
        self.fig.tight_layout()

    def plot_heatmap(self, ax):
        import numpy as np
        _, bar_data = self.get_chart_data()
        testcases, data = bar_data['testcases'], bar_data['data']
        types = ["ERROR", "FATAL", "WARNING"]
        arr = np.array([[data[tc][typ] for typ in types] for tc in testcases])
        if not np.any(arr):
            ax.text(0.5, 0.5, "No data", ha='center', va='center')
            return
        cax = ax.imshow(arr, aspect='auto', cmap='viridis')
        ax.set_xticks(np.arange(len(types)))
        ax.set_xticklabels(types)
        ax.set_yticks(np.arange(len(testcases)))
        ax.set_yticklabels(testcases)
        ax.set_xlabel("Error Type")
        ax.set_ylabel("Test Case")
        ax.set_title("Heatmap of Error Frequency by Test Case")
        self.fig.colorbar(cax, ax=ax, label="Count")
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                count = arr[i, j]
                if count > 0:
                    ax.text(j, i, str(count), ha='center', va='center',
                            color='white' if count > arr.max()/2 else 'black',
                            fontsize=10, fontweight='bold')
        self.fig.tight_layout()

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Chart as Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
        if path:
            try:
                self.fig.savefig(path)
                QMessageBox.information(self, "Export", f"Chart exported to {path}")
                logger.info(f"Chart exported to {path}.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export chart:\n{e}")
                logger.error(f"Export Error", f"Failed to export chart:{e}")

class FeaturesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Features")
        self.resize(800, 600)  # Initial size, but user can resize/maximize

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setHtml(self.get_features_html())
        layout.addWidget(self.text_edit)

        btn = QPushButton("Close", self)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_features_html(self):
        return (
            "<h2>LogTriage Application – Features</h2>"
            "<ol>"
            "<li><b>Log File Loading</b><ul>"
            "<li>Load and parse simulation/compile log files (<code>.log</code>, <code>.log.gz</code>) from folders, including recursive search.</li>"
            "<li>Supports both <code>simulate.log</code> and <code>compile.log</code> files.</li>"
            "<li>Progress bar and status messages during long operations.</li>"
            "<li>Recent folders menu for quick access.</li>"
            "</ul></li>"
            "<li><b>Tabular Log View</b><ul>"
            "<li>Display log messages in a table with columns: <i>ID, Test Case, Test Option, Type, Count, Message, Log Type, Log File Path, Excluded, Comments</i>.</li>"
            "<li>Double-click a row to open the corresponding log file in an external editor.</li>"
            "</ul></li>"
            "<li><b>Filtering and Sorting</b><ul>"
            "<li>Per-column filtering: supports text, regex, numeric, and exclusion status filters.</li>"
            "<li>Multi-column sorting: Shift+Click on headers to sort by multiple columns.</li>"
            "</ul></li>"
            "<li><b>Find and Highlight</b><ul>"
            "<li>Find dialog with regex support and row highlighting for quick search.</li>"
            "</ul></li>"
            "<li><b>Exclusion List Management</b><ul>"
            "<li>Add messages to an exclusion list.</li>"
            "<li>View, import, export, and clear the exclusion list.</li>"
            "<li>Visual indication for excluded rows.</li>"
            "<li>Filter to show only excluded or only non-excluded rows.</li>"
            "</ul></li>"
            "<li><b>Comments</b><ul>"
            "<li>Add per-row comments (editable, multi-line, persistent).</li>"
            "<li>Comments are saved and loaded with session files.</li>"
            "</ul></li>"
            "<li><b>Export and Import</b><ul>"
            "<li>Export filtered or selected rows to CSV.</li>"
            "<li>Export summary table to CSV.</li>"
            "<li>Export exclusion list to CSV.</li>"
            "<li>Import exclusion list from CSV.</li>"
            "<li>Export charts as images.</li>"
            "</ul></li>"
            "<li><b>Session Management</b><ul>"
            "<li>Save/load session (including comments and exclusions) for later review or sharing.</li>"
            "</ul></li>"
            "<li><b>Summary and Statistics</b><ul>"
            "<li>Summary dialog: per-testcase/testopt counts for <b>ERROR</b>, <b>FATAL</b>, <b>WARNING</b> (total and unique).</li>"
            "<li>Quick menu option to display current filtered row count and unique count in the status bar.</li>"
            "</ul></li>"
            "<li><b>Visualization</b><ul>"
            "<li>Pie chart: Distribution of error types.</li>"
            "<li>Grouped bar chart: Error/Fatal/Warning counts by test case.</li>"
            "<li>Heatmap: Error frequency by test case, with selectable color schemes and cell count annotations.</li>"
            "<li>Export all charts as images.</li>"
            "</ul></li>"
            "<li><b>User Interface and Usability</b><ul>"
            "<li>Dark mode toggle for comfortable viewing.</li>"
            "<li>Keyboard shortcuts for all major actions (see Help &gt; Shortcut Keys).</li>"
            "<li>Status bar shows current row count, unique count, and error statistics.</li>"
            "<li>Progress bar and status messages for long operations.</li>"
            "<li>Memory usage warning for large datasets.</li>"
            "</ul></li>"
            "<li><b>Robustness and Help</b><ul>"
            "<li>Robust error handling and logging (errors are logged to <code>tool_error.log</code>).</li>"
            "<li>Help menu with shortcut keys, features, and author info.</li>"
            "</ul></li>"
            "</ol>"
        )

class ExclusionListDialog(QDialog):
    def __init__(self, exclusion_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exclusion List")
        self.resize(600, 400)
        layout = QVBoxLayout(self)

        # Add count label
        count_label = QLabel(f"Total excluded messages: {len(exclusion_list)}")
        logger.info(f"Total excluded messages: {len(exclusion_list)}.")
        layout.addWidget(count_label)

        self.table = QTableWidget(len(exclusion_list), 1)
        self.table.setHorizontalHeaderLabels(["Excluded Message"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, msg in enumerate(sorted(exclusion_list)):
            item = QTableWidgetItem(msg)
            self.table.setItem(i, 0, item)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn = QPushButton("Close", self)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class FindDialog(QDialog):
    def __init__(self, parent, table, columns):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.resize(400, 100)
        self.table = table
        self.columns = columns
        self.matches = []
        self.current = -1
        layout = QVBoxLayout(self)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Enter search text (supports regex)...")
        layout.addWidget(self.input)
        from PyQt5.QtWidgets import QCheckBox
        self.regex_checkbox = QCheckBox("Regex", self)
        layout.addWidget(self.regex_checkbox)
        btns = QHBoxLayout()
        self.find_btn = QPushButton("Find All", self)
        self.find_btn.clicked.connect(self.find_all)
        btns.addWidget(self.find_btn)
        self.next_btn = QPushButton("Find Next", self)
        self.next_btn.clicked.connect(self.find_next)
        btns.addWidget(self.next_btn)
        self.close_btn = QPushButton("Close", self)
        self.close_btn.clicked.connect(self.close)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)
        self.input.returnPressed.connect(self.find_all)
        self.input.setFocus()
        self.highlight_role = Qt.yellow

    def find_all(self):
        term = self.input.text().strip()
        self.clear_highlight()
        self.matches = []
        if not term:
            return
        use_regex = self.regex_checkbox.isChecked()
        try:
            if use_regex:
                pattern = re.compile(term, re.IGNORECASE)
            else:
                pattern = None
        except re.error as e:
            QMessageBox.warning(self, "Regex Error", f"Invalid regex pattern:\n{e}")
            logger.error(f"Regex Error, Invalid regex pattern:{e}.")
            return

        for i in range(self.table.rowCount()):
            for j in range(self.table.columnCount()):
                cell_text = str(self.table.item(i, j).text())
                if use_regex:
                    if pattern.search(cell_text):
                        self.matches.append(i)
                        break
                else:
                    if term.lower() in cell_text.lower():
                        self.matches.append(i)
                        break
        for i in self.matches:
            for j in range(self.table.columnCount()):
                self.table.item(i, j).setBackground(self.highlight_role)
        if self.matches:
            self.table.selectRow(self.matches[0])
            self.current = 0
        else:
            QMessageBox.information(self, "Find", "No matches found.")
            logger.warning(f"Find", "No matches found.")

    def find_next(self):
        if not self.matches:
            self.find_all()
            return
        self.current = (self.current + 1) % len(self.matches)
        self.table.selectRow(self.matches[self.current])

    def clear_highlight(self):
        for i in range(self.table.rowCount()):
            for j in range(self.table.columnCount()):
                self.table.item(i, j).setBackground(Qt.white)

class SummaryDialog(QDialog):
    def __init__(self, summary_rows, parent=None, statusbar=None):
        super().__init__(parent)
        self.setWindowTitle("Summary Table")
        self.resize(900, 400)
        self.statusbar = statusbar
        self.all_rows = summary_rows
        self.filtered_rows = summary_rows.copy()
        self.filters = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        headers = ["Test Case", "Test Option", "ERROR", "ERROR (unique)", "FATAL", "FATAL (unique)", "WARNING", "WARNING (unique)"]
        self.table = QTableWidget(len(self.all_rows), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for i, row in enumerate(self.all_rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        layout.addWidget(self.table)
        # Export button
        export_btn = QPushButton("Export Summary to CSV", self)
        export_btn.clicked.connect(self.export_summary)
        layout.addWidget(export_btn)

    def apply_filters(self):
        self.update_comments_dict_from_table()
        filters = [edit.text().strip().lower() for edit in self.filters]
        self.filtered_rows = []
        for row in self.all_rows:
            match = True
            for i, f in enumerate(filters):
                if f and f not in str(row[i]).lower():
                    match = False
                    break
            if match:
                self.filtered_rows.append(row)
        self.populate_table(self.filtered_rows)

    def populate_table(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))

    def export_summary(self):
        try:
            default_dir = os.getcwd()
            path, _ = QFileDialog.getSaveFileName(self, "Export Summary to CSV", default_dir, "CSV Files (*.csv)")
            if not path:
                return
            path = path.strip()
            with open(path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])
                for i in range(self.table.rowCount()):
                    row = [self.table.item(i, j).text() for j in range(self.table.columnCount())]
                    writer.writerow(row)
            if self.statusbar:
                self.statusbar.showMessage(f"Summary exported to {path}")
                logger.info(f"Summary exported to {path}.")
            QMessageBox.information(self, "Export", f"Summary exported to {path}")
        except Exception as e:
            if self.statusbar:
                self.statusbar.showMessage(f"Failed to export summary: {e}")
                logger.error(f"Failed to export summary: {e}.")
            QMessageBox.critical(self, "Export Error", f"Failed to export summary:\n{e}")

class CommentEditDialog(QDialog):
    def __init__(self, initial_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Comment")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)
        btns = QHBoxLayout()
        ok_btn = QPushButton("OK", self)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def get_text(self):
        return self.text_edit.toPlainText()

class LogTriageWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.patterns_file = os.path.join(os.path.dirname(__file__), "patterns.csv")
        logger.info(f"Loading {self.patterns_file} for pattern search...")
        self.patterns = load_patterns_from_file(self.patterns_file)
        self.is_loading = False
        self.stop_requested = False
        self.comments_dict = {}  # {row_key: comment}
        self.setWindowTitle("Log Triage v7.0")
        self.columns = ["ID", "Test Case", "Test Option", "Type", "Count", "Message", "Log Type", "Log File Path", "Line Number", "Excluded", "Comments"]
        self.settings = QSettings("LogTriage", "LogTriageApp")
        self.all_rows = []
        self.filtered_rows = []
        self.sort_order = []
        self.loaded_folder = ""
        self.show_simulate = True
        self.show_compile = True
        self.show_scoreboard = True
        self.logfile_column_visible = True 
        self.init_ui()
        self.restore_settings()
        self.exclusion_list = set()
        self.show_only_excluded = False
        self.show_only_nonexcluded = False

    def init_ui(self):
        default_colwidths = [100, 250, 300, 200, 80, 400, 80, 500, 100]
        central = QWidget()
        vbox = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Table
        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.handle_table_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        self.table.horizontalHeader().sectionResized.connect(self.update_filter_row_geometry)
        self.table.horizontalHeader().sectionMoved.connect(self.update_filter_row_geometry)
        self.table.horizontalScrollBar().valueChanged.connect(self.update_filter_row_geometry)
        self.table.viewport().installEventFilter(self)
        self.table.verticalScrollBar().valueChanged.connect(self.update_filter_row_geometry)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().geometriesChanged.connect(self.update_filter_row_geometry)  # Add this if available
        self.table.itemChanged.connect(self.handle_comment_edit)
        self.table.itemSelectionChanged.connect(self.update_selection_status)

        # --- Filter row widget (floating, below header) ---
        self.filter_row_widget = QWidget()
        self.filter_row_widget.setObjectName("filter_row_widget")
        filter_layout = QHBoxLayout(self.filter_row_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_edits = []
        for i, col in enumerate(self.columns):
            edit = QLineEdit()
            edit.setPlaceholderText(f"Filter {col} (use | for OR)")
            edit.textChanged.connect(self.apply_filters)
            filter_layout.addWidget(edit)
            self.filter_edits.append(edit)

        self.filter_row_widget.setParent(self.table.viewport())
        self.filter_row_widget.raise_()

        # Add filter row and table to layout (filter row first)
        vbox.addWidget(self.filter_row_widget)
        vbox.addWidget(self.table)

        # Set default column widths
        for i, w in enumerate(default_colwidths):
            self.table.setColumnWidth(i, w)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnHidden(7, False)

        # Folder path label (above progress bar)
        self.folder_status_label = QLabel("")
        self.folder_status_label.setStyleSheet("font-size: 10pt;")
        vbox.addWidget(self.folder_status_label)

        # Progress bar (below folder path label)
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setFormat("")  # We'll set this dynamically
        vbox.addWidget(self.progress)

        self.stop_btn = QPushButton("Stop Loading", self)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_loading)
        vbox.addWidget(self.stop_btn)

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Menu bar
        self.menu = self.menuBar()
        self.init_menus()

        # Keyboard shortcuts for context menu actions
        self.copy_action = QAction("Copy Row", self)
        self.copy_action.setShortcut("Ctrl+C")
        self.copy_action.triggered.connect(self.copy_selected_rows)
        self.addAction(self.copy_action)

        self.excl_action = QAction("Add to Exclusion", self)
        self.excl_action.setShortcut("Ctrl+X")
        self.excl_action.triggered.connect(self.add_to_exclusion)
        self.addAction(self.excl_action)

        self.find_action = QAction("Find", self)
        self.find_action.setShortcut("Ctrl+F")
        self.find_action.triggered.connect(self.show_find_dialog)
        self.addAction(self.find_action)

    def commit_active_editor(self):
        """If a cell editor is open, commit its data before refreshing the table."""
        if self.table.state() == QAbstractItemView.EditingState:
            self.table.closePersistentEditor(self.table.currentItem())
            self.table.clearFocus()
            QApplication.processEvents()

    def load_patterns_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Patterns File", os.getcwd(), "CSV Files (*.csv)")
        if not path:
            return
        try:
            self.patterns = load_patterns_from_file(path)
            self.patterns_file = path
            QMessageBox.information(self, "Patterns Loaded", f"Patterns loaded from {path}")
            self.statusbar.showMessage("Patterns Loaded", f"Patterns loaded from {path}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load patterns file:\n{e}")

    # --- Persistence ---
    def save_recent_folders(self, folder):
        folders = self.load_recent_folders()
        if folder in folders:
            folders.remove(folder)
        folders.insert(0, folder)
        folders = [f for f in folders if os.path.isdir(f)]
        folders = folders[:MAX_RECENT_FOLDERS]
        self.settings.setValue(RECENT_FOLDERS_KEY, folders)
        self.recent_folders = folders

    def stop_loading(self):
        self.stop_requested = True
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.statusbar.showMessage("Loading stopped by user. Waiting for worker to finish...")
            logger.info(f"Loading stopped by user. Waiting for worker to finish...")
        # Do not update the table here; wait for on_parse_finished

    def load_recent_folders(self):
        return self.settings.value(RECENT_FOLDERS_KEY, [], type=list)

    def save_col_widths(self):
        widths = [self.table.columnWidth(i) for i in range(len(self.columns))]
        self.settings.setValue(COL_WIDTHS_KEY, widths)

    def restore_col_widths(self):
        widths = self.settings.value(COL_WIDTHS_KEY, [], type=list)
        if widths and len(widths) == len(self.columns):
            for i, w in enumerate(widths):
                self.table.setColumnWidth(i, int(w))

    def eventFilter(self, obj, event):
        if obj == self.table.viewport() and event.type() == event.Resize:
            self.update_filter_row_geometry()
        return super().eventFilter(obj, event)

    def save_settings(self):
        self.save_col_widths()
        self.settings.setValue(WIN_SIZE_KEY, self.size())
        self.settings.setValue(WIN_POS_KEY, self.pos())
        self.settings.setValue(EXCLUSION_LIST_KEY, list(self.exclusion_list))

    def restore_settings(self):
        size = self.settings.value(WIN_SIZE_KEY)
        pos = self.settings.value(WIN_POS_KEY)
        if size:
            self.resize(size)
        if pos:
            self.move(pos)
        self.restore_col_widths()

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def reset_filters(self):
        for edit in self.filter_edits:
            edit.clear()

    def update_filter_row_geometry(self):
        header = self.table.horizontalHeader()
        y = header.height() - 1  # Just below the header
        x_offset = -self.table.horizontalScrollBar().value()
        self.filter_row_widget.move(x_offset, y)
        self.filter_row_widget.setFixedHeight(self.filter_row_widget.sizeHint().height())
        # Set width and position of each filter box to match column
        for i, edit in enumerate(self.filter_edits):
            x = self.table.columnViewportPosition(i)
            w = self.table.columnWidth(i)
            edit.setGeometry(x, 0, w, self.filter_row_widget.height())
        # Set the filter row widget width to match the table viewport
        self.filter_row_widget.setFixedWidth(self.table.viewport().width())

    def handle_comment_edit(self, item):
        comments_col = self.columns.index("Comments")
        if item.column() == comments_col:
            # Get the row key from the first column's UserRole
            row_key = self.table.item(item.row(), 0).data(Qt.UserRole)
            self.comments_dict[row_key] = item.text()

    def toggle_show_only_excluded(self):
        self.show_only_excluded = self.show_only_excluded_action.isChecked()
        if self.show_only_excluded:
            # Uncheck the other action
            self.show_only_nonexcluded = False
            self.show_only_nonexcluded_action.setChecked(False)
        self.apply_filters()
    
    def toggle_show_only_nonexcluded(self):
        self.show_only_nonexcluded = self.show_only_nonexcluded_action.isChecked()
        if self.show_only_nonexcluded:
            # Uncheck the other action
            self.show_only_excluded = False
            self.show_only_excluded_action.setChecked(False)
        self.apply_filters()

    def update_selection_status(self):
        selected_rows = {item.row() for item in self.table.selectedItems()}
        self.statusbar.showMessage(f"{len(selected_rows)} row(s) selected.")
        logger.info(f"{len(selected_rows)} row(s) selected.")

    def show_visualization_dialog(self):
        dlg = VisualizationDialog(self, self.get_visualization_data, self.dark_mode_action.isChecked())
        dlg.exec_()

    def get_visualization_data(self):
        # Pie chart data
        stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
        for row in self.filtered_rows:
            if row.type in stats:
                stats[row.type] += int(row.count)
        # Bar/heatmap data
        testcases = sorted({row.testcase for row in self.filtered_rows})
        types = ["ERROR", "FATAL", "WARNING"]
        data = {tc: {typ: 0 for typ in types} for tc in testcases}
        for row in self.filtered_rows:
            tc = row.testcase
            typ = row.type
            if tc in data and typ in data[tc]:
                data[tc][typ] += int(row.count)
        return stats, {"testcases": testcases, "data": data}

    def get_message_stats(self):
        """
        Returns a dict with total and unique counts for ERROR, FATAL, WARNING.
        """
        stats = {
            "ERROR": {"total": 0, "unique": set()},
            "FATAL": {"total": 0, "unique": set()},
            "WARNING": {"total": 0, "unique": set()},
        }
        for row in self.filtered_rows:
            typ = row.type
            count = int(row.count)
            msg = row.message
            if typ in stats:
                stats[typ]["total"] += count
                stats[typ]["unique"].add(msg)
        # Convert sets to counts
        for typ in stats:
            stats[typ]["unique"] = len(stats[typ]["unique"])
        return stats

    # --- Menus ---
    def init_menus(self):
        # File menu
        file_menu = self.menu.addMenu("&File")
        load_action = QAction("Load Log Folder", self)
        load_action.setShortcut("Ctrl+O")  # Changed from Ctrl+L to Ctrl+O
        load_action.triggered.connect(self.load_log_folder)
        file_menu.addAction(load_action)
    
        reload_action = QAction("Reload", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_last_folder)
        file_menu.addAction(reload_action)
    
        file_menu.addSeparator()
        load_patterns_action = QAction("Load Patterns File...", self)
        load_patterns_action.setShortcut("Ctrl+P")
        load_patterns_action.triggered.connect(self.load_patterns_file)
        file_menu.addAction(load_patterns_action)  # or settings_menu.addAction(...)

        export_action = QAction("Export to CSV", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)
    
        file_menu.addSeparator()
        recent_menu = QMenu("Recent Folders", self)
        self.recent_menu = recent_menu
        self.update_recent_menu()
        file_menu.addMenu(recent_menu)
        file_menu.addSeparator()
    
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
        # Edit menu
        edit_menu = self.menu.addMenu("&Edit")
        copy_row_action = QAction("Copy Selected Row(s)", self)
        copy_row_action.setShortcut("Ctrl+C")
        copy_row_action.triggered.connect(self.copy_selected_rows)
        edit_menu.addAction(copy_row_action)
    
        find_action = QAction("Find", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)
    
        # Columns menu
        columns_menu = self.menu.addMenu("&Columns")
        self.column_actions = []
        for i, col in enumerate(self.columns):
            if col == "Line Number":
                continue  # Skip adding "Line Number" to the Columns menu
            act = QAction(col, self, checkable=True)
            act.setChecked(True)
            act.triggered.connect(partial(self.toggle_column, i))
            columns_menu.addAction(act)
            self.column_actions.append(act)

        # Log menu
        log_menu = self.menu.addMenu("&Log")
        self.simulate_action = QAction("Show simulate.log", self, checkable=True)
        self.simulate_action.setChecked(True)
        self.simulate_action.setShortcut("Ctrl+1")
        self.simulate_action.triggered.connect(self.toggle_simulate)
        log_menu.addAction(self.simulate_action)
    
        self.compile_action = QAction("Show compile.log", self, checkable=True)
        self.compile_action.setChecked(True)
        self.compile_action.setShortcut("Ctrl+2")
        self.compile_action.triggered.connect(self.toggle_compile)
        log_menu.addAction(self.compile_action)
    
        log_menu.addSeparator()
        self.scoreboard_action = QAction("Show Scoreboard Errors", self, checkable=True)
        self.scoreboard_action.setChecked(True)
        self.scoreboard_action.setShortcut("Ctrl+3")
        self.scoreboard_action.triggered.connect(self.toggle_scoreboard)
        log_menu.addAction(self.scoreboard_action)
    
        # Exclusion menu
        exclusion_menu = self.menu.addMenu("&Exclusion")
        add_excl_action = QAction("Add to Exclusion", self)
        add_excl_action.setShortcut("Ctrl+X")
        add_excl_action.triggered.connect(self.add_to_exclusion)
        exclusion_menu.addAction(add_excl_action)
    
        view_excl_action = QAction("View Exclusion List", self)
        view_excl_action.setShortcut("Ctrl+Shift+V")
        view_excl_action.triggered.connect(self.view_exclusion)
        exclusion_menu.addAction(view_excl_action)
    
        export_excl_action = QAction("Export Exclusion List", self)
        export_excl_action.setShortcut("Ctrl+Shift+E")
        export_excl_action.triggered.connect(self.export_exclusion_list)
        exclusion_menu.addAction(export_excl_action)
    
        import_excl_action = QAction("Import Exclusion List", self)
        import_excl_action.setShortcut("Ctrl+Shift+I")
        import_excl_action.triggered.connect(self.import_exclusion_list)
        exclusion_menu.addAction(import_excl_action)
    
        clear_excl_action = QAction("Clear Exclusion List", self)
        clear_excl_action.setShortcut("Ctrl+Shift+C")
        clear_excl_action.triggered.connect(self.clear_exclusion)
        exclusion_menu.addAction(clear_excl_action)
    
        file_menu.addSeparator()
        self.show_only_excluded_action = QAction("Show Only Excluded Rows", self, checkable=True)
        self.show_only_excluded_action.setShortcut("Ctrl+Shift+X")
        self.show_only_excluded_action.setChecked(False)
        self.show_only_excluded_action.triggered.connect(self.toggle_show_only_excluded)
        exclusion_menu.addAction(self.show_only_excluded_action)
    
        self.show_only_nonexcluded_action = QAction("Show Only Non-Excluded Rows", self, checkable=True)
        self.show_only_nonexcluded_action.setShortcut("Ctrl+Shift+N")
        self.show_only_nonexcluded_action.setChecked(False)
        self.show_only_nonexcluded_action.triggered.connect(self.toggle_show_only_nonexcluded)
        exclusion_menu.addAction(self.show_only_nonexcluded_action)
        file_menu.addSeparator()
    
        # Session menu
        session_menu = self.menu.addMenu("&Session")
        save_session_action = QAction("Save Session", self)
        save_session_action.setShortcut("Ctrl+Shift+S")
        save_session_action.triggered.connect(self.save_session)
        session_menu.addAction(save_session_action)
    
        load_session_action = QAction("Load Session", self)
        load_session_action.setShortcut("Ctrl+Shift+O")
        load_session_action.triggered.connect(self.load_session)
        session_menu.addAction(load_session_action)
    
        # Summary menu
        summary_menu = self.menu.addMenu("&Summary")
        show_summary_action = QAction("Show Summary", self)
        show_summary_action.setShortcut("Ctrl+S")
        show_summary_action.triggered.connect(self.show_summary)
        summary_menu.addAction(show_summary_action)
        
        # Add this for quick row stats
        show_row_stats_action = QAction("Show Row Stats", self)
        show_row_stats_action.setShortcut("Ctrl+Shift+R")
        show_row_stats_action.triggered.connect(self.show_row_stats)
        summary_menu.addAction(show_row_stats_action)

        # Settings menu
        settings_menu = self.menu.addMenu("&Settings")
        self.dark_mode_action = QAction("Dark Mode", self, checkable=True)
        self.dark_mode_action.setShortcut("Ctrl+D")
        self.dark_mode_action.setChecked(False)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        settings_menu.addAction(self.dark_mode_action)
    
        # Visualization menu
        visual_menu = self.menu.addMenu("&Visualization")
        visualize_action = QAction("Open Visualization Window", self)
        visualize_action.setShortcut("Ctrl+T")
        visualize_action.triggered.connect(self.show_visualization_dialog)
        visual_menu.addAction(visualize_action)

        # Help menu
        help_menu = self.menu.addMenu("&Help")
        shortcut_action = QAction("Shortcut Keys", self)
        shortcut_action.setShortcut("F1")
        shortcut_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcut_action)
    
        features_action = QAction("Features", self)
        features_action.setShortcut("F2")
        features_action.triggered.connect(self.show_features)
        help_menu.addAction(features_action)
    
        author_action = QAction("Author", self)
        author_action.setShortcut("F3")
        author_action.triggered.connect(self.show_author)
        help_menu.addAction(author_action)

    def update_recent_menu(self):
        self.recent_menu.clear()
        folders = self.load_recent_folders()
        if not folders:
            self.recent_menu.addAction("(No recent folders)").setEnabled(False)
        else:
            for folder in folders:
                act = QAction(folder, self)
                act.triggered.connect(lambda checked, f=folder: self.load_log_folder(f))
                self.recent_menu.addAction(act)

    # --- Log Loading ---
    def set_loading_ui(self, loading):
        self.stop_btn.setEnabled(loading)
        self.menu.setEnabled(not loading)
        # Optionally, disable/enable specific actions if you want finer control

    def load_log_folder(self, folder=None):
        if self.is_loading:
            QMessageBox.warning(self, "Loading in Progress", "A folder is already being loaded. Please wait until it finishes or stop the current load.")
            logger.warning(f"Loading in Progress", "A folder is already being loaded. Please wait until it finishes or stop the current load.")
            return
        self.is_loading = True
        self.set_loading_ui(True)
        if not folder:
            last_folder = self.settings.value("lastFolder", "")
            folder = QFileDialog.getExistingDirectory(self, "Select Log Folder", last_folder or "")
            if not folder:
                self.is_loading = False
                self.set_loading_ui(False)
                return
            folder = folder.strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Path", f"The path '{folder}' is not a valid directory.")
            logger.warning(f"Invalid Path", f"The path '{folder}' is not a valid directory.")
            self.is_loading = False
            self.set_loading_ui(False)
            return
        self.loaded_folder = folder
        self.settings.setValue(LAST_FOLDER_KEY, folder)
        self.save_recent_folders(folder)
        self.update_recent_menu()
        QApplication.processEvents()
        # Find log files
        log_files = []
        for root, dirs, files in os.walk(folder):
            for fname in files:
                if (self.show_simulate and fname.startswith("simulate.log")) or (self.show_compile and fname.startswith("compile.log")):
                    if fname.endswith(".log") or fname.endswith(".log.gz"):
                        log_files.append(os.path.join(root, fname))
        if not log_files:
            self.statusbar.showMessage("No valid log files found in the selected folder.")
            logger.warning(f"No valid log files found in the selected folder.")
            self.progress.setMaximum(1)
            self.progress.setValue(1)
            self.progress.setFormat("No log files found.")
            self.is_loading = False
            self.set_loading_ui(False)
            return
        self.progress.setMaximum(len(log_files))
        self.progress.setValue(0)
        self.progress.setFormat(f"Loading 0/{len(log_files)} files...")
    
        self.statusbar.showMessage(f"Loading log file folder path: {folder} ...")
        logger.info(f"Loading log file folder path: {folder} ...")
    
        self.stop_requested = False
        self.worker = LogParseWorker(log_files, self.show_simulate, self.show_compile, self.show_scoreboard, self.patterns)
        self.worker.progress.connect(self.on_parse_progress)
        self.worker.finished.connect(self.on_parse_finished)
        self.worker.start()

    def on_parse_progress(self, current, total):
        self.progress.setValue(current)
        self.progress.setFormat(f"Loading {current}/{total} files...")
        QApplication.processEvents()
    
    def on_parse_finished(self, all_rows):
        self.is_loading = False
        self.set_loading_ui(False)
        self.progress.setValue(self.progress.maximum())
        self.progress.setFormat(f"Loaded {self.progress.value()}/{self.progress.maximum()} files.")
        logger.info(f"Loaded {self.progress.value()}/{self.progress.maximum()} files.")
        self.folder_status_label.setText(f"Loaded log file folder path: {self.loaded_folder}")
        logger.info(f"Loaded log file folder path: {self.loaded_folder}")
        self.all_rows = group_rows(all_rows)
        self.filtered_rows = self.all_rows.copy()
        self.apply_filters()
        self.update_table()
        if self.stop_requested:
            self.statusbar.showMessage("Loading stopped by user. Partial results shown.")
            logger.info(f"Loading stopped by user. Partial results shown.")
        else:
            self.statusbar.showMessage("All files loaded.")
            logger.info(f"All files loaded.")

    def reload_last_folder(self):
        folder = self.settings.value(LAST_FOLDER_KEY, "")
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Reload", "No valid last loaded folder found.")
            logger.warning(f"Reload, No valid last loaded folder found.")
            return
        self.load_log_folder(folder)

    # --- Filtering and Sorting ---
    def match_advanced_filter(self, cell_value, filter_expr):
        expr = filter_expr.strip()
        if not expr:
            return True
        # Split by | for OR
        or_parts = [part.strip() for part in expr.split('|')]
        for or_part in or_parts:
            if or_part.lower() in cell_value.lower():
                return True
        return False

    def apply_filters(self):
        filters = [edit.text().strip().lower() for edit in self.filter_edits]
        self.filtered_rows = []
        for row in self.all_rows:
            match = True
            for i, f in enumerate(filters):
                if not f:
                    continue
                col_name = self.columns[i]
                if col_name == "Count":
                    if not parse_count_filter(f, row.count):
                        match = False
                        break
                elif col_name == "Excluded":
                    is_excluded = row.message in self.exclusion_list
                    if (f in ["yes", "y", "1", "true"] and not is_excluded) or (f in ["no", "n", "0", "false"] and is_excluded):
                        match = False
                        break
                    if f not in ["yes", "y", "1", "true", "no", "n", "0", "false"]:
                        if (f not in ("yes" if is_excluded else "no")):
                            match = False
                            break
                elif col_name == "Comments":
                    # Usually skip filtering on comments, or implement if needed
                    continue
                else:
                    attr = self._colname_to_attr(col_name)
                    if not self.match_advanced_filter(str(getattr(row, attr)), f):
                        match = False
                        break
            if not match:
                continue
    
            # --- Exclusion filter logic (NEW) ---
            is_excluded = row.message in self.exclusion_list
            if self.show_only_excluded and not is_excluded:
                continue
            if self.show_only_nonexcluded and is_excluded:
                continue
            # -------------------------------------
    
            # Only filter scoreboard errors here
            if not self.show_scoreboard and "sbd_compare" in str(row.message).lower():
                continue
            self.filtered_rows.append(row)
        self.update_table()
        unique_rows = {self.get_row_key(row) for row in self.filtered_rows}
        stats = self.get_message_stats()
        mem = get_memory_usage_mb()
        self.statusbar.showMessage(
            f"Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
            f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
            f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
            f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
        )
        logger.info(
            f"Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
            f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
            f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
            f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
        )
        if mem > 1000:
            QMessageBox.warning(self, "Memory Usage Warning",
                f"High memory usage detected: {mem:.1f} MB.\n"
                "Consider filtering or reducing the number of loaded files.")
            logger.warning(f"Memory Usage Warning. High memory usage detected: {mem:.1f} MB. Consider filtering or reducing the number of loaded files.")

    def _colname_to_attr(self, col):
        mapping = {
            "ID": "id",
            "Test Case": "testcase",
            "Test Option": "testopt",
            "Type": "type",
            "Count": "count",
            "Message": "message",
            "Log Type": "logtype",
            "Log File Path": "logfilepath",
            "Line Number": "linenumber"
        }
        return mapping.get(col, col.lower().replace(" ", ""))

    def populate_table_rows(self):
        self.table.setRowCount(len(self.filtered_rows))
        comments_col = self.columns.index("Comments")
        for i, row in enumerate(self.filtered_rows):
            is_excluded = row.message in self.exclusion_list
            row_key = self.get_row_key(row)
            for j, col in enumerate(self.columns):
                if col == "Excluded":
                    item = QTableWidgetItem("Yes" if is_excluded else "No")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                elif col == "Comments":
                    comment = self.comments_dict.get(row_key, "")
                    item = QTableWidgetItem(comment)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    attr = self._colname_to_attr(col)
                    value = getattr(row, attr)
                    item = QTableWidgetItem(str(value))
                    if j == 0:
                        item.setData(Qt.UserRole, row_key)
                    # Color coding
                    if row.type == "ERROR":
                        item.setForeground(Qt.red)
                    elif row.type == "FATAL":
                        item.setForeground(Qt.magenta)
                    elif row.type == "WARNING":
                        item.setForeground(Qt.darkYellow)
                    # Tooltips
                    if attr in ["testopt", "message", "logfilepath"]:
                        item.setToolTip(str(value))
                if is_excluded:
                    item.setBackground(Qt.lightGray)
                self.table.setItem(i, j, item)
        self.table.setColumnHidden(7, False)
        self.update_filter_row_geometry()

    def update_table(self, sort=True):
        self.table.setSortingEnabled(False)
        self.populate_table_rows()
        if sort and self.sort_order:
            self.sort_table_multi()
        self.table.setSortingEnabled(True)

    # --- Multi-column sorting ---
    def handle_header_click(self, logicalIndex):
        if logicalIndex >= len(self.columns):
            return
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            if logicalIndex in self.sort_order:
                self.sort_order.remove(logicalIndex)
            self.sort_order.append(logicalIndex)
        else:
            self.sort_order = [logicalIndex]
        self.sort_table_multi()

    def sort_table_multi(self):
        if not self.sort_order:
            return
        # Only use valid indices
        valid_sort_order = [i for i in self.sort_order if i < len(self.columns)]
        if not valid_sort_order:
            return
    
        # Only sort by columns that are LogRow attributes
        logrow_attrs = {"id", "testcase", "testopt", "type", "count", "message", "logtype", "logfilepath", "linenumber"}
        def sort_key(row):
            key = []
            for i in valid_sort_order:
                attr = self._colname_to_attr(self.columns[i])
                if attr in logrow_attrs:
                    key.append(getattr(row, attr))
                elif self.columns[i] == "Excluded":
                    key.append(row.message in self.exclusion_list)
                elif self.columns[i] == "Comments":
                    row_key = (
                        row.id, row.testcase, row.testopt, row.type,
                        row.message, row.logtype, row.logfilepath, row.linenumber
                    )
                    key.append(self.comments_dict.get(row_key, ""))
                else:
                    key.append("")  # fallback
            return tuple(key)
    
        self.filtered_rows.sort(key=sort_key)
        self.update_table(sort=False)

    # --- Export ---
    def export_to_csv(self):
        self.update_comments_dict_from_table()  # <-- This must be the first line!
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Export to CSV")
        msg_box.setText("Export which data to CSV?")
        all_btn = msg_box.addButton("All Rows", QMessageBox.AcceptRole)
        sel_btn = msg_box.addButton("Selected Rows", QMessageBox.AcceptRole)
        cancel_btn = msg_box.addButton(QMessageBox.Cancel)
        msg_box.setDefaultButton(all_btn)
        msg_box.exec_()
    
        if msg_box.clickedButton() == cancel_btn:
            return
        elif msg_box.clickedButton() == sel_btn:
            export_type = "selected"
        else:
            export_type = "all"
    
        export_columns = self.columns
    
        export_rows = []
        if export_type == "selected":
            selected = self.table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "Export", "No rows selected.")
                return
            rows = {}
            for item in selected:
                row = item.row()
                if row not in rows:
                    # Build the row from the table, including Excluded and Comments
                    row_data = []
                    for col in range(self.table.columnCount()):
                        cell = self.table.item(row, col)
                        row_data.append(cell.text() if cell else "")
                    rows[row] = row_data
            export_rows = list(rows.values())
            pass
        else:
            for row in self.filtered_rows:
                is_excluded = row.message in self.exclusion_list
                row_key = (
                    row.id, row.testcase, row.testopt, row.type,
                    row.message, row.logtype, row.logfilepath, row.linenumber
                )
                comment = self.comments_dict.get(row_key, "")
                row_with_excl = [
                    row.id, row.testcase, row.testopt, row.type, row.count,
                    row.message, row.logtype, row.logfilepath, row.linenumber,
                    "Yes" if is_excluded else "No", comment
                ]
                export_rows.append(row_with_excl)
        if not export_rows:
            QMessageBox.warning(self, "Export", "No data to export.")
            logger.warning(f"Export, No data to export.")
            return
    
        path, _ = QFileDialog.getSaveFileName(self, "Export to CSV", os.getcwd(), "CSV Files (*.csv)")
        if not path or not path.strip():
            return
        path = path.strip()
        try:
            with open(path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(export_columns)
                for row in export_rows:
                    writer.writerow(row)
            self.statusbar.showMessage(f"Exported {len(export_rows)} {export_type} rows to {path}")
            logger.warning(f"Exported {len(export_rows)} {export_type} rows to {path}")
            excluded_count = sum(1 for row in export_rows if row[self.columns.index("Excluded")] == "Yes")
            QMessageBox.information(self, "Export Info",
                f"Exported {len(export_rows)} {export_type} rows to {path}\n"
                f"Unique rows: {len({tuple(row) for row in export_rows})}\n"
                f"Excluded rows in export: {excluded_count}")
        except Exception as e:
            self.statusbar.showMessage(f"Failed to export: {e}")
            logger.error(f"Failed to export: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    # --- Exclusion ---
    def add_to_exclusion(self):
        self.commit_active_editor()  # <-- Add this line FIRST
        self.update_comments_dict_from_table()
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Exclusion", "No rows selected.")
            return
        rows = set()
        for item in selected:
            row = item.row()
            msg = self.table.item(row, 5).text()
            rows.add(msg)
        self.exclusion_list.update(rows)
        self.apply_filters()
        self.statusbar.showMessage(f"Added {len(rows)} messages to exclusion list.")
        logger.info(f"Added {len(rows)} messages to exclusion list.")

    def view_exclusion(self):
        dlg = ExclusionListDialog(self.exclusion_list, self)
        dlg.exec_()

    def export_exclusion_list(self):
        self.update_comments_dict_from_table()  # <-- This must be the first line!
        path, _ = QFileDialog.getSaveFileName(self, "Export Exclusion List", os.getcwd(), "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Message", "Comment"])
                for msg in sorted(self.exclusion_list):
                    comment = ""
                    for logrow in self.all_rows:
                        if logrow.message == msg:
                            row_key = (
                                logrow.id, logrow.testcase, logrow.testopt, logrow.type,
                                logrow.message, logrow.logtype, logrow.logfilepath, logrow.linenumber
                            )
                            comment = self.comments_dict.get(row_key, "")
                            if comment:
                                break
                    writer.writerow([msg, comment])
            self.statusbar.showMessage(f"Exclusion list exported to {path}")
            logger.info(f"Exclusion list exported to {path}.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export exclusion list:\n{e}")
            logger.error(f"Export Error, Failed to export exclusion list:{e}")

    def import_exclusion_list(self):
        self.update_comments_dict_from_table()  # <-- This must be the first line!
        path, _ = QFileDialog.getOpenFileName(self, "Import Exclusion List", os.getcwd(), "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    msg = row["Message"]
                    comment = row.get("Comment", "")
                    self.exclusion_list.add(msg)
                    # For all rows in current data with this message, set the comment
                    for logrow in self.all_rows:
                        # If logrow is a LogRow object
                        if hasattr(logrow, 'message'):
                            if logrow.message == msg:
                                row_key = (
                                    logrow.id, logrow.testcase, logrow.testopt, logrow.type,
                                    logrow.message, logrow.logtype, logrow.logfilepath, logrow.linenumber
                                )
                                self.comments_dict[row_key] = comment
                        # If logrow is a dict
                        elif isinstance(logrow, dict):
                            if logrow.get('message') == msg:
                                row_key = (
                                    logrow.get('id'), logrow.get('testcase'), logrow.get('testopt'), logrow.get('type'),
                                    logrow.get('message'), logrow.get('logtype'), logrow.get('logfilepath'), logrow.get('linenumber')
                                )
                                self.comments_dict[row_key] = comment
            self.apply_filters()
            self.update_table()
            self.statusbar.showMessage(f"Exclusion list imported from {path} and applied to current data.")
            logger.info(f"Exclusion list imported from {path} and applied to current data.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import exclusion list:\n{e}")
            logger.error(f"Import Error, Failed to import exclusion list:{e}")

    def clear_exclusion(self):
        self.update_comments_dict_from_table()  # <-- This must be the first line!
        self.exclusion_list.clear()
        self.apply_filters()
        self.statusbar.showMessage("Exclusion list cleared.")
        logger.info(f"Exclusion list cleared.")

    # --- Summary ---
    def show_summary(self):
        summary = defaultdict(lambda: {"ERROR":0, "FATAL":0, "WARNING":0})
        unique_msgs = defaultdict(lambda: {"ERROR": set(), "FATAL": set(), "WARNING": set()})
        excluded_counts = defaultdict(lambda: {"ERROR":0, "FATAL":0, "WARNING":0})
        log_types = defaultdict(set)
    
        # Only process rows with non-empty Test Case and Test Option
        for row in self.filtered_rows:
            testcase = row.testcase
            testopt = row.testopt
            if not testcase or not testopt:
                continue
            typ = row.type
            count = int(row.count)
            msg = row.message
            log_type = row.logtype  # "simulate" or "compile"
            summary[(testcase, testopt)][typ] += count
            unique_msgs[(testcase, testopt)][typ].add(msg)
            if msg in self.exclusion_list:
                excluded_counts[(testcase, testopt)][typ] += count
            log_types[(testcase, testopt)].add(log_type)
    
        summary_rows = []
        for (testcase, testopt), counts in summary.items():
            # Only add rows with at least one non-zero count
            if (counts["ERROR"] == 0 and counts["FATAL"] == 0 and counts["WARNING"] == 0):
                continue
            log_type_set = log_types[(testcase, testopt)]
            compile_present = "Yes" if "compile" in log_type_set else "No"
            simulate_present = "Yes" if "simulate" in log_type_set else "No"
            summary_rows.append([
                testcase, testopt,
                counts["ERROR"], len(unique_msgs[(testcase, testopt)]["ERROR"]),
                counts["FATAL"], len(unique_msgs[(testcase, testopt)]["FATAL"]),
                counts["WARNING"], len(unique_msgs[(testcase, testopt)]["WARNING"]),
            ])
        # Update SummaryDialog to accept and display these columns
        dlg = SummaryDialog(summary_rows, self, statusbar=self.statusbar)
        dlg.exec_()

    def show_row_stats(self):
        row_count = len(self.filtered_rows)
        unique_row_count = len({self.get_row_key(row) for row in self.filtered_rows})
        stats = self.get_message_stats()
        msg = (f"Showing {row_count} rows | Unique rows: {unique_row_count} | "
               f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
               f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
               f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)")
        self.statusbar.showMessage(msg)
        logger.info(f"{msg}.")

    # --- Context Menu ---
    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy Row (Ctrl+C)", self)
        copy_action.triggered.connect(self.copy_selected_rows)
        menu.addAction(copy_action)
        excl_action = QAction("Add to Exclusion (Ctrl+X)", self)
        excl_action.triggered.connect(self.add_to_exclusion)
        menu.addAction(excl_action)
        # Add the new action here
        show_all_comments_action = QAction("Show All Comments", self)
        show_all_comments_action.triggered.connect(self.show_all_comments_for_selected_row)
        menu.addAction(show_all_comments_action)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def show_all_comments_for_selected_row(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        logrow = self.get_logrow_for_table_row(row)
        row_key = self.get_row_key(logrow)
        comment = self.comments_dict.get(row_key, "")
        msg = comment if comment.strip() else "(No comments)"
        QMessageBox.information(self, "All Comments", msg)

    def show_shortcuts(self):
        QMessageBox.information(self, "Shortcut Keys",
            "File Menu:\n"
            "  Ctrl+O: Load Log Folder\n"
            "  Ctrl+R: Reload\n"
            "  Ctrl+P: Load Patterns File\n"
            "  Ctrl+E: Export to CSV\n"
            "  Ctrl+Q: Exit\n"
            "\n"
            "Edit Menu:\n"
            "  Ctrl+C: Copy Selected Row(s)\n"
            "  Ctrl+F: Find\n"
            "\n"
            "Exclusion Menu:\n"
            "  Ctrl+X: Add to Exclusion\n"
            "  Ctrl+Shift+V: View Exclusion List\n"
            "  Ctrl+Shift+E: Export Exclusion List\n"
            "  Ctrl+Shift+I: Import Exclusion List\n"
            "  Ctrl+Shift+C: Clear Exclusion List\n"
            "  Ctrl+Shift+X: Show Only Excluded Rows\n"
            "  Ctrl+Shift+N: Show Only Non-Excluded Rows\n"
            "\n"
            "Log Menu:\n"
            "  Ctrl+1: Show simulate.log\n"
            "  Ctrl+2: Show compile.log\n"
            "  Ctrl+3: Show Scoreboard Errors\n"
            "\n"
            "Summary Menu:\n"
            "  Ctrl+S: Show Summary\n"
            # Add this line for your new shortcut:
            "  Ctrl+Shift+R: Show Row Stats\n"
            "\n"
            "Session Menu:\n"
            "  Ctrl+Shift+S: Save Session\n"
            "  Ctrl+Shift+O: Load Session\n"
            "\n"
            "Settings Menu:\n"
            "  Ctrl+D: Dark Mode\n"
            "\n"
            "Help Menu:\n"
            "  F1: Shortcut Keys\n"
            "  F2: Features\n"
            "  F3: Author\n"
        )

    def show_features(self):
        dlg = FeaturesDialog(self)
        dlg.exec_()

    def show_author(self):
        QMessageBox.information(self, "Author",
            "LogTriage Application\n"
            "Author: Johnson Amalraj (I77655) with help of https://chatbot/\n"
            "Contact: johnson.amalraj@microchip.com"
        )

    def copy_selected_rows(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        rows = {}
        for item in selected:
            row = item.row()
            if row not in rows:
                rows[row] = [self.table.item(row, col).text() for col in range(self.table.columnCount())]
        text = "\n".join(["\t".join(row) for row in rows.values()])
        QApplication.clipboard().setText(text)
        self.statusbar.showMessage("Copied selected row(s) to clipboard.")
        logger.info(f"Copied selected row(s) to clipboard.")

    def toggle_column(self, col_index):
        checked = self.column_actions[col_index].isChecked()
        self.table.setColumnHidden(col_index, not checked)
        self.update_filter_row_geometry()

    def open_log_file(self, index):
        row = index.row()
        filepath = self.table.item(row, 7).text()
        try:
            lineno = int(self.table.item(row, 8).text())
        except Exception:
            lineno = 1
        if os.path.isfile(filepath):
            # For gvim, use +{lineno} to jump to line
            os.system(f"gvim '+{lineno}' '{filepath}' &")
        else:
            QMessageBox.warning(self, "Open Log File", f"File not found:\n{filepath}")
            logger.warning(f"Open Log File", f"File not found:\n{filepath}.")

    def handle_table_double_click(self, index):
        if index.column() == len(self.columns) - 1:  # Comments column
            current_text = self.table.item(index.row(), index.column()).text()
            dlg = CommentEditDialog(current_text, self)
            if dlg.exec_() == QDialog.Accepted:
                new_text = dlg.get_text()
                self.table.item(index.row(), index.column()).setText(new_text)
                logrow = self.get_logrow_for_table_row(index.row())
                row_key = self.get_row_key(logrow)
                self.comments_dict[row_key] = new_text
        else:
            self.open_log_file(index)

    # --- Log menu actions ---
    def toggle_simulate(self):
        self.show_simulate = self.simulate_action.isChecked()
        self.apply_filters()
    
    def toggle_compile(self):
        self.show_compile = self.compile_action.isChecked()
        self.apply_filters()

    def toggle_scoreboard(self):
        self.show_scoreboard = self.scoreboard_action.isChecked()
        self.apply_filters()

    def save_session(self):
        self.update_comments_dict_from_table()  # <-- This must be the first line!
        default_dir = os.getcwd()
        comments_col = self.columns.index("Comments")
        for row in range(self.table.rowCount()):
            item = self.table.item(row, comments_col)
            if item is not None:
                self.table.closePersistentEditor(item)
        self.table.clearFocus()
        QApplication.processEvents()
        self.update_comments_dict_from_table()
    
        path, _ = QFileDialog.getSaveFileName(self, "Save Session", default_dir, "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# LogTriage Session File v1\n")
                f.write("[ROWS]\n")
                writer = csv.writer(f)
                # Save all rows (without Excluded and Comments, as Excluded is derived and Comments is separate)
                data_columns = [col for col in self.columns if col not in ("Excluded", "Comments")]
                writer.writerow(data_columns)
                for row in self.filtered_rows:
                    writer.writerow([
                        row.id, row.testcase, row.testopt, row.type, row.count,
                        row.message, row.logtype, row.logfilepath, row.linenumber
                    ])
                f.write("[COMMENTS]\n")
                for key, comment in self.comments_dict.items():
                    writer.writerow(list(key) + [comment])
                f.write("[EXCLUSIONS]\n")
                for msg in self.exclusion_list:
                    writer.writerow([msg])
            self.statusbar.showMessage(f"Session saved to {path}")
            logger.info(f"Session saved to {path}.")
        except Exception as e:
            QMessageBox.critical(self, "Save Session Error", f"Failed to save session:\n{e}")
            logger.error(f"Save Session Error, Failed to save session:{e}")

    def update_comments_dict_from_table(self):
        comments_col = self.columns.index("Comments")
        for row in range(self.table.rowCount()):
            row_key = self.table.item(row, 0).data(Qt.UserRole)
            comment_item = self.table.item(row, comments_col)
            comment = comment_item.text() if comment_item else ""
            self.comments_dict[row_key] = comment

    def get_logrow_for_table_row(self, row_idx):
        # self.filtered_rows is in the same order as the table
        return self.filtered_rows[row_idx]

    def get_row_key(self, row):
        return (
            row.id, row.testcase, row.testopt, row.type,
            row.message, row.logtype, row.logfilepath, row.linenumber
        )

    def load_session(self):
        default_dir = os.getcwd()
        path, _ = QFileDialog.getOpenFileName(self, "Load Session", default_dir, "CSV Files (*.csv)")
        if not path:
            return
        try:
            self.progress.setFormat("Loading session file...")
            self.progress.setMaximum(0)
            self.progress.setValue(0)
            self.save_recent_folders(os.path.dirname(path))
            self.update_recent_menu()
            QApplication.processEvents()
    
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() == "[ROWS]":
                        break
                header = next(csv.reader([f.readline()]))
                rows = []
                for row in csv.reader(f):
                    if row and row[0].startswith("["):
                        section_header = row[0]
                        break
                    if len(row) >= 9:
                        rows.append(LogRow(*row[:9]))
                else:
                    section_header = None

                comments_dict = {}
                if section_header == "[COMMENTS]":
                    for row in csv.reader(f):
                        if row and row[0].startswith("["):
                            section_header = row[0]
                            break
                        if not row or len(row) < len(self.columns) - 2 + 1:
                            logger.error(f"Skipping malformed comment row: {row}")
                            continue
                        row_key = tuple(row[:ROW_KEY_LEN])
                        comment = row[ROW_KEY_LEN]
                        comments_dict[row_key] = comment
                else:
                    comments_dict = {}
    
                exclusion_list = set()
                if section_header == "[EXCLUSIONS]":
                    for row in csv.reader(f):
                        if row and not row[0].startswith("["):
                            exclusion_list.add(row[0])

    
            self.all_rows = rows
            self.comments_dict = comments_dict
            self.exclusion_list = exclusion_list
            self.filtered_rows = self.all_rows.copy()
            self.apply_filters()
            self.update_table()
            stats = self.get_message_stats()
            mem = get_memory_usage_mb()
            self.folder_status_label.setText(f"Loaded session file: {os.path.basename(path)}")
            logger.info(f"Loaded session file: {os.path.basename(path)}")
            self.statusbar.showMessage(
                f"Session loaded from {path} | Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
                f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
                f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
                f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
            )
            logger.info(
                f"Session loaded from {path} | Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
                f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
                f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
                f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
            )
    
            self.progress.setMaximum(1)
            self.progress.setValue(1)
            self.progress.setFormat("Session loaded.")
            logger.info(f"Session loaded.")
            QApplication.processEvents()
        except Exception as e:
            self.progress.setFormat("Failed to load session.")
            QMessageBox.critical(self, "Load Session Error", f"Failed to load session:\n{e}")
            logger.error(f"Load Session Error, Failed to load session:{e}.")

    def toggle_dark_mode(self):
        if self.dark_mode_action.isChecked():
            dark_stylesheet = """
            QWidget {
                background-color: #232629;
                color: #F0F0F0;
            }
            QTableWidget {
                background-color: #232629;
                color: #F0F0F0;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #31363b;
                color: #F0F0F0;
            }
            QLineEdit, QTextEdit {
                background-color: #31363b;
                color: #F0F0F0;
                border: 1px solid #444;
            }
            QWidget#filter_row_widget {
                background: #232629;
                color: #F0F0F0;
                border-bottom: 1px solid #444;
            }
            QMenuBar, QMenu {
                background-color: #232629;
                color: #F0F0F0;
            }
            QMenuBar::item:selected {
                background: #0078d7;   /* A bright blue, or pick your own */
                color: #ffffff;
            }
            QMenu::item:selected {
                background: #0078d7;   /* Same blue as above */
                color: #ffffff;
            }
            QStatusBar {
                background-color: #232629;
                color: #F0F0F0;
            }
            QLabel {
                color: #F0F0F0;
                background: transparent;
            }
            QProgressBar {
                background-color: #31363b;
                color: #F0F0F0;
                border: 1px solid #444;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
            }
            QPushButton {
                background-color: #31363b;
                color: #F0F0F0;
                border: 1px solid #444;
            }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("")

    # --- Find dialog ---
    def show_find_dialog(self):
        dlg = FindDialog(self, self.table, self.columns)
        dlg.exec_()

class LogParseWorker(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)      # all_rows

    def __init__(self, log_files, show_simulate, show_compile, show_scoreboard, patterns):
        super().__init__()
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
            logger.info(f"Processing file {idx+1}/{len(self.log_files)}: {filepath}")
            id_val, testcase, testopt = extract_log_info(filepath)
            error_counts, fatal_counts, warning_counts = parse_log_file(filepath, self.patterns)
            for (msg, lineno), count in error_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="ERROR",
                    count=count,
                    message=msg,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)
            for (msg, lineno), count in fatal_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="FATAL",
                    count=count,
                    message=msg,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)
            for (msg, lineno), count in warning_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = LogRow(
                    id=id_val,
                    testcase=testcase,
                    testopt=testopt,
                    type="WARNING",
                    count=count,
                    message=msg,
                    logtype="simulate" if "simulate" in os.path.basename(filepath) else "compile",
                    logfilepath=filepath,
                    linenumber=lineno
                )
                all_rows.append(row)
            self.progress.emit(idx+1, len(self.log_files))
        self.finished.emit(all_rows)

    def stop(self):
        self._stop_requested = True

if __name__ == "__main__":

    logfile = 'tool_process.log'  # or 'tool_process.txt'
    if os.path.exists(logfile):
        os.remove(logfile)

    # --- Custom FileHandler that flushes after every log message ---
    class FlushFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()

    # --- Set up logging ---
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # File handler (immediate flush)
    file_handler = FlushFileHandler(logfile, mode='w', encoding='utf-8', delay=False)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (optional, for real-time feedback)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # --- Example log messages (remove or keep as needed) ---
    logging.info("Tool started")

    def log_uncaught_exceptions(exctype, value, tb):
        error_msg = "".join(traceback.format_exception(exctype, value, tb))
        logger.error("Uncaught exception:\n%s", error_msg)
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Unexpected Error",
            f"An unexpected error occurred:\n\n{value}\n\nSee {logfile} for details.")

    sys.excepthook = log_uncaught_exceptions

    # --- Start the PyQt5 application ---
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = LogTriageWindow()
    win.show()
    sys.exit(app.exec_())
