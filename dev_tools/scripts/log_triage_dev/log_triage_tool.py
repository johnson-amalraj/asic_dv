import sys
import os
import csv
import gzip
import re
import logging
import traceback
import psutil
import matplotlib

from collections import Counter, defaultdict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHBoxLayout, QLineEdit, QLabel, QProgressBar, QMenuBar, QMenu, QAction, QMessageBox,
    QAbstractItemView, QHeaderView, QStatusBar, QDialog, QPushButton, QInputDialog, QMenu, QTextEdit, QToolBar, 
    QCheckBox, QWidgetAction
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QSize
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.use('Qt5Agg')

SETTINGS_ORG = "LogTriage"
SETTINGS_APP = "LogTriageApp"

RECENT_FOLDERS_KEY = "recentFolders"
EXCLUSION_LIST_KEY = "exclusionList"
LAST_FOLDER_KEY = "lastFolder"
COL_WIDTHS_KEY = "colWidths"
WIN_SIZE_KEY = "winSize"
WIN_POS_KEY = "winPos"

MAX_RECENT_FOLDERS = 5

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

def parse_log_file(filepath):
    """
    Parse a log file and extract error, fatal, and warning messages from
    VCS, Questa, Xcelium, UVM, xmelab, and -E-/F-/W- formats.
    """
    patterns = [
        # UVM
        ('ERROR',   re.compile(r'UVM_ERROR'),   r'^.*UVM_ERROR\s*:? ?'),
        ('WARNING', re.compile(r'UVM_WARNING'), r'^.*UVM_WARNING\s*:? ?'),
        ('FATAL',   re.compile(r'UVM_FATAL'),   r'^.*UVM_FATAL\s*:? ?'),

        # Questa/ModelSim
        ('ERROR',   re.compile(r'^\*\* Error:'),   r'^\*\* Error:\s*'),
        ('WARNING', re.compile(r'^\*\* Warning:'), r'^\*\* Warning:\s*'),
        ('FATAL',   re.compile(r'^\*\* Fatal:'),   r'^\*\* Fatal:\s*'),

        # VCS
        ('ERROR',   re.compile(r'^Error-$$.*?$$'),   r'^Error-$$.*?$$\s*'),
        ('WARNING', re.compile(r'^Warning-$$.*?$$'), r'^Warning-$$.*?$$\s*'),
        ('FATAL',   re.compile(r'^Fatal:'),          r'^Fatal:\s*'),

        # Xcelium (ncvlog/ncsim)
        ('ERROR',   re.compile(r'ncvlog: \*E,'),   r'^.*ncvlog: \*E,[^:]*:?\s*'),
        ('WARNING', re.compile(r'ncvlog: \*W,'),   r'^.*ncvlog: \*W,[^:]*:?\s*'),
        ('FATAL',   re.compile(r'ncsim: \*F,'),    r'^.*ncsim: \*F,[^:]*:?\s*'),

        # xmelab
        ('ERROR',   re.compile(r'xmelab: \*E,'),   r'^.*xmelab: \*E,[^:]*:?\s*'),
        ('WARNING', re.compile(r'xmelab: \*W,'),   r'^.*xmelab: \*W,[^:]*:?\s*'),

        # -E-, -F-, -W- patterns
        ('ERROR',   re.compile(r'^-E-'), r'^-E-\s*'),
        ('FATAL',   re.compile(r'^-F-'), r'^-F-\s*'),
        ('WARNING', re.compile(r'^-W-'), r'^-W-\s*'),

        # *E, *F, *W patterns (sometimes used)
        ('ERROR',   re.compile(r'^\*E'), r'^\*E\s*'),
        ('FATAL',   re.compile(r'^\*F'), r'^\*F\s*'),
        ('WARNING', re.compile(r'^\*W'), r'^\*W\s*'),

        # Generic (case-insensitive, less specific, so last)
        ('ERROR',   re.compile(r'\bError\b', re.IGNORECASE),   r'^.*Error\s*:? ?'),
        ('WARNING', re.compile(r'\bWarning\b', re.IGNORECASE), r'^.*Warning\s*:? ?'),
        ('FATAL',   re.compile(r'\bFatal\b', re.IGNORECASE),   r'^.*Fatal\s*:? ?'),
    ]

    errors, fatals, warnings = [], [], []

    with open_log_file_anytype(filepath) as f:
        for line in f:
            line_stripped = line.strip()
            for typ, pat, prefix in patterns:
                if pat.search(line_stripped):
                    msg = re.sub(prefix, '', line_stripped)
                    msg = clean_message(msg)
                    if is_uvm_summary_line(line_stripped):
                        break  # skip this line
                    if typ == 'ERROR':
                        errors.append(msg)
                    elif typ == 'WARNING':
                        warnings.append(msg)
                    elif typ == 'FATAL':
                        fatals.append(msg)
                    break  # Only match the first pattern per line

    error_counts = Counter(errors)
    fatal_counts = Counter(fatals)
    warning_counts = Counter(warnings)
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
    grouped = defaultdict(lambda: [None, None, None, None, 0, None, None, None, None])
    for row in rows:
        # Key: (Test Case, Test Option, Type, Message, Log Type)
        key = (row[1], row[2], row[3], row[5], row[6])
        if grouped[key][0] is None:
            grouped[key][0] = row[0]  # ID (first one)
            grouped[key][1] = row[1]  # Test Case
            grouped[key][2] = row[2]  # Test Option
            grouped[key][3] = row[3]  # Type
            grouped[key][4] = 0       # Count (sum)
            grouped[key][5] = row[5]  # Message
            grouped[key][6] = row[6]  # Log Type
            grouped[key][7] = row[7]  # Log File Path
            grouped[key][8] = row[8] if len(row) > 8 else ""  # Comments, if present
        grouped[key][4] += int(row[4])  # Sum Count
    return list(grouped.values())

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
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export chart:\n{e}")

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
                    row = [self.table.item(i, j).text() if self.table.item(i, j) else "" for j in range(self.table.columnCount())]
                    writer.writerow(row)
            if self.statusbar:
                self.statusbar.showMessage(f"Summary exported to {path}")
            QMessageBox.information(self, "Export", f"Summary exported to {path}")
        except Exception as e:
            if self.statusbar:
                self.statusbar.showMessage(f"Failed to export summary: {e}")
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
        self.comments_dict = {}  # {row_key: comment}
        self.setWindowTitle("Log Triage v5.0")
        self.columns = ["ID", "Test Case", "Test Option", "Type", "Count", "Message", "Log Type", "Log File Path", "Excluded", "Comments"]
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
            edit.setPlaceholderText(f"Filter {col}")
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
            # Get the row's unique key (excluding Comments)
            row_data = []
            for col in range(len(self.columns) - 1):
                cell = self.table.item(item.row(), col)
                row_data.append(cell.text() if cell else "")
            row_key = tuple(row_data)
            # Store the entire comment (multi-line)
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

    def show_pie_chart(self):
        from matplotlib.figure import Figure
        from PyQt5.QtWidgets import QComboBox
    
        testcases = sorted({row[1] for row in self.filtered_rows})
        combo = QComboBox()
        combo.addItem("All Test Cases")
        combo.addItems(testcases)
    
        def plot_pie(ax):
            selected_tc = combo.currentText()
            stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
            for row in self.filtered_rows:
                if selected_tc != "All Test Cases" and row[1] != selected_tc:
                    continue
                if row[3] in stats:
                    stats[row[3]] += int(row[4])
            labels = []
            sizes = []
            for typ in ["ERROR", "FATAL", "WARNING"]:
                if stats[typ] > 0:
                    labels.append(f"{typ} ({stats[typ]})")
                    sizes.append(stats[typ])
            if sizes:
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#e74c3c', '#8e44ad', '#f1c40f'])
                ax.set_title("Distribution of Error Types")
            else:
                ax.text(0.5, 0.5, "No data", ha='center', va='center')
    
        fig = Figure(figsize=(5, 4))
        ax = fig.add_subplot(111)
        plot_pie(ax)
    
        def on_filter_change():
            fig.clf()
            ax = fig.add_subplot(111)
            plot_pie(ax)
            dialog.canvas.draw()
    
        dialog = ChartDialog(fig, "Pie Chart: Error Types", self, filter_widgets=[combo], on_filter_change=on_filter_change)
        dialog.exec_()

    def show_heatmap_chart(self):
        import numpy as np
        from PyQt5.QtWidgets import QComboBox
    
        testcases = sorted({row[1] for row in self.filtered_rows})
        types = ["ERROR", "FATAL", "WARNING"]
        data = np.zeros((len(testcases), len(types)), dtype=int)
        tc_idx = {tc: i for i, tc in enumerate(testcases)}
        typ_idx = {typ: i for i, typ in enumerate(types)}
        for row in self.filtered_rows:
            tc = row[1]
            typ = row[3]
            if tc in tc_idx and typ in typ_idx:
                data[tc_idx[tc], typ_idx[typ]] += int(row[4])
        if not np.any(data):
            QMessageBox.information(self, "Heatmap", "No error/warning/fatal data to plot.")
            return
    
        colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis', 'hot', 'OrRd', 'YlOrRd']
        cmap_combo = QComboBox()
        cmap_combo.addItems(colormaps)
        cmap_combo.setCurrentText('viridis')
    
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        colorbar = [None]
    
        def plot_heatmap(ax, cmap_name):
            ax.clear()
            cax = ax.imshow(data, aspect='auto', cmap=cmap_name)
            ax.set_xticks(np.arange(len(types)))
            ax.set_xticklabels(types)
            ax.set_yticks(np.arange(len(testcases)))
            ax.set_yticklabels(testcases)
            ax.set_xlabel("Error Type")
            ax.set_ylabel("Test Case")
            ax.set_title("Heatmap of Error Frequency by Test Case")
            if colorbar[0] is not None:
                colorbar[0].remove()
            colorbar[0] = fig.colorbar(cax, ax=ax, label="Count")
            fig.tight_layout()
            # Annotate each cell with the count
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    count = data[i, j]
                    if count > 0:
                        ax.text(j, i, str(count), ha='center', va='center',
                                color='white' if count > data.max()/2 else 'black',
                                fontsize=10, fontweight='bold')
    
        plot_heatmap(ax, cmap_combo.currentText())
    
        def on_cmap_change():
            plot_heatmap(ax, cmap_combo.currentText())
            dialog.canvas.draw()
    
        cmap_combo.currentIndexChanged.connect(on_cmap_change)
    
        dialog = ChartDialog(fig, "Heatmap: Error Frequency", self, filter_widgets=[cmap_combo])
        dialog.exec_()

    def show_grouped_bar_chart(self):
        import numpy as np
        from PyQt5.QtWidgets import QComboBox
    
        testcases = sorted({row[1] for row in self.filtered_rows})
        types = ["ERROR", "FATAL", "WARNING"]
        data = np.zeros((len(testcases), len(types)), dtype=int)
        tc_idx = {tc: i for i, tc in enumerate(testcases)}
        typ_idx = {typ: i for i, typ in enumerate(types)}
        for row in self.filtered_rows:
            tc = row[1]
            typ = row[3]
            if tc in tc_idx and typ in typ_idx:
                data[tc_idx[tc], typ_idx[typ]] += int(row[4])
        if not np.any(data):
            QMessageBox.information(self, "Bar Chart", "No error/warning/fatal data to plot.")
            return
    
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        x = np.arange(len(testcases))
        width = 0.25
    
        colors = ['#e74c3c', '#8e44ad', '#f1c40f']  # ERROR, FATAL, WARNING
        bars = []
        for i, typ in enumerate(types):
            bars.append(ax.bar(x + i*width - width, data[:, i], width, label=typ, color=colors[i]))
    
        ax.set_xticks(x)
        ax.set_xticklabels(testcases, rotation=45, ha='right')
        ax.set_ylabel("Count")
        ax.set_xlabel("Test Case")
        ax.set_title("Error/Fatal/Warning Counts by Test Case")
        ax.legend()
        fig.tight_layout()
    
        # Annotate bars with counts
        for bar_group in bars:
            for bar in bar_group:
                height = bar.get_height()
                if height > 0:
                    ax.annotate(f'{int(height)}',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),  # 3 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
        dialog = ChartDialog(fig, "Grouped Bar Chart: Error Types by Test Case", self)
        dialog.exec_()

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
            typ = row[3]
            count = int(row[4])
            msg = row[5]
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
            act = QAction(col, self, checkable=True)
            act.setChecked(True)
            act.triggered.connect(lambda checked, idx=i: self.toggle_column(idx, checked))
            columns_menu.addAction(act)
            self.column_actions.append(act)
    
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
    
        # Settings menu
        settings_menu = self.menu.addMenu("&Settings")
        self.dark_mode_action = QAction("Dark Mode", self, checkable=True)
        self.dark_mode_action.setShortcut("Ctrl+D")
        self.dark_mode_action.setChecked(False)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        settings_menu.addAction(self.dark_mode_action)
    
        # Visualization menu
        visual_menu = self.menu.addMenu("&Visualization")
        pie_action = QAction("Pie Chart: Error Types", self)
        pie_action.triggered.connect(self.show_pie_chart)
        visual_menu.addAction(pie_action)
        
        heatmap_action = QAction("Heatmap: Error Frequency", self)
        heatmap_action.triggered.connect(self.show_heatmap_chart)
        visual_menu.addAction(heatmap_action)

        # In your init_menus() under Visualization menu:
        bar_action = QAction("Grouped Bar Chart: Error Types by Test Case", self)
        bar_action.triggered.connect(self.show_grouped_bar_chart)
        visual_menu.addAction(bar_action)

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
    def load_log_folder(self, folder=None):
        if not folder:
            last_folder = self.settings.value("lastFolder", "")
            folder = QFileDialog.getExistingDirectory(self, "Select Log Folder", last_folder or "")
            if not folder:
                return
            folder = folder.strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Path", f"The path '{folder}' is not a valid directory.")
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
        # --- Add this block ---
        if not log_files:
            self.statusbar.showMessage("No valid log files found in the selected folder.")
            self.progress.setMaximum(1)
            self.progress.setValue(1)
            self.progress.setFormat("No log files found.")
            return
        # ----------------------
        self.progress.setMaximum(len(log_files))
        self.progress.setValue(0)
        self.progress.setFormat(f"Loading 0/{len(log_files)} files...")
    
        self.statusbar.showMessage(f"Loading log file folder path: {folder} ...")

        # Start worker thread
        self.worker = LogParseWorker(log_files, self.show_simulate, self.show_compile, self.show_scoreboard)
        self.worker.progress.connect(self.on_parse_progress)
        self.worker.finished.connect(self.on_parse_finished)
        self.worker.start()
    
    def on_parse_progress(self, current, total):
        self.progress.setValue(current)
        self.progress.setFormat(f"Loading {current}/{total} files...")
        QApplication.processEvents()
    
    def on_parse_finished(self, all_rows):
        self.progress.setValue(self.progress.maximum())
        self.progress.setFormat(f"Loaded {self.progress.maximum()}/{self.progress.maximum()} files.")
        self.folder_status_label.setText(f"Loaded log file folder path: {self.loaded_folder}")
        self.all_rows = group_rows(all_rows)
        self.filtered_rows = self.all_rows.copy()
        self.apply_filters()
        self.update_table()

    def reload_last_folder(self):
        folder = self.settings.value(LAST_FOLDER_KEY, "")
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Reload", "No valid last loaded folder found.")
            return
        self.load_log_folder(folder)

    # --- Filtering and Sorting ---
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
                    if not parse_count_filter(f, row[self.columns.index("Count")]):
                        match = False
                        break
                elif col_name == "Excluded":
                    is_excluded = row[5] in self.exclusion_list
                    if (f in ["yes", "y", "1", "true"] and not is_excluded) or (f in ["no", "n", "0", "false"] and is_excluded):
                        match = False
                        break
                    # If filter is not a recognized value, do substring match
                    if f not in ["yes", "y", "1", "true", "no", "n", "0", "false"]:
                        if (f not in ("yes" if is_excluded else "no")):
                            match = False
                            break
                else:
                    # Map i to the correct index in row (since row doesn't have Excluded/Comments)
                    excluded_idx = self.columns.index("Excluded")
                    comments_idx = self.columns.index("Comments")
                    if i < excluded_idx:
                        row_index = i
                    elif i < comments_idx:
                        row_index = i - 1
                    else:
                        continue
                    if f not in str(row[row_index]).lower():
                        match = False
                        break
            if not match:
                continue
    
            # --- Exclusion filter logic (NEW) ---
            is_excluded = row[5] in self.exclusion_list
            if self.show_only_excluded and not is_excluded:
                continue
            if self.show_only_nonexcluded and is_excluded:
                continue
            # -------------------------------------
    
            # Only filter scoreboard errors here
            if not self.show_scoreboard and "sbd_compare" in str(row[5]).lower():
                continue
            self.filtered_rows.append(row)
        self.update_table()
        unique_rows = {tuple(row) for row in self.filtered_rows}
        stats = self.get_message_stats()
        mem = get_memory_usage_mb()
        self.statusbar.showMessage(
            f"Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
            f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
            f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
            f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
        )
        if mem > 1000:
            QMessageBox.warning(self, "Memory Usage Warning",
                f"High memory usage detected: {mem:.1f} MB.\n"
                "Consider filtering or reducing the number of loaded files.")

    def populate_table_rows(self):
        self.table.setRowCount(len(self.filtered_rows))
        for i, row in enumerate(self.filtered_rows):
            is_excluded = row[5] in self.exclusion_list  # Message column
            for j, col in enumerate(self.columns):
                if col == "Excluded":
                    item = QTableWidgetItem("Yes" if is_excluded else "No")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Read-only
                elif col == "Comments":
                    row_key = tuple(row)  # row does not include Excluded or Comments
                    comment = self.comments_dict.get(row_key, "")
                    item = QTableWidgetItem(comment)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    excluded_idx = self.columns.index("Excluded")
                    comments_idx = self.columns.index("Comments")
                    if j < excluded_idx:
                        row_index = j
                    elif j < comments_idx:
                        row_index = j - 1
                    else:
                        continue  # Should not happen
            
                    # Only for the "Count" column, set integer data for sorting
                    if col == "Count":
                        item = QTableWidgetItem(str(row[row_index]))
                        try:
                            item.setData(Qt.EditRole, int(row[row_index]))
                        except Exception:
                            item.setData(Qt.EditRole, 0)  # fallback if conversion fails
                    else:
                        item = QTableWidgetItem(str(row[row_index]))
            
                    # Color coding
                    if row[3] == "ERROR":
                        item.setForeground(Qt.red)
                    elif row[3] == "FATAL":
                        item.setForeground(Qt.magenta)
                    elif row[3] == "WARNING":
                        item.setForeground(Qt.darkYellow)
                    # Tooltips
                    if row_index in [2, 5, 7]:  # Test Option, Message, Log File Path
                        item.setToolTip(str(row[row_index]))
                # Grey out excluded rows
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
        def sort_key(row):
            return tuple(row[i] for i in valid_sort_order)
        self.filtered_rows.sort(key=sort_key)
        self.update_table(sort=False)

    # --- Export ---
    def export_to_csv(self):
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
        else:
            for row in self.filtered_rows:
                is_excluded = row[5] in self.exclusion_list
                row_key = tuple(row)
                comment = self.comments_dict.get(row_key, "")
                # Compose the row with Excluded and Comments
                row_with_excl = list(row) + [("Yes" if is_excluded else "No"), comment]
                export_rows.append(row_with_excl)
    
        if not export_rows:
            QMessageBox.warning(self, "Export", "No data to export.")
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
            excluded_count = sum(1 for row in export_rows if row[self.columns.index("Excluded")] == "Yes")
            QMessageBox.information(self, "Export Info",
                f"Exported {len(export_rows)} {export_type} rows to {path}\n"
                f"Unique rows: {len({tuple(row) for row in export_rows})}\n"
                f"Excluded rows in export: {excluded_count}")
        except Exception as e:
            self.statusbar.showMessage(f"Failed to export: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    # --- Exclusion ---
    def add_to_exclusion(self):
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

    def view_exclusion(self):
        dlg = ExclusionListDialog(self.exclusion_list, self)
        dlg.exec_()

    def export_exclusion_list(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Exclusion List", os.getcwd(), "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                for msg in sorted(self.exclusion_list):
                    writer.writerow([msg])
            self.statusbar.showMessage(f"Exclusion list exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export exclusion list:\n{e}")

    def import_exclusion_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Exclusion List", os.getcwd(), "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                self.exclusion_list = set(row[0] for row in reader if row)
            self.apply_filters()
            self.update_table()
            self.statusbar.showMessage(f"Exclusion list imported from {path} and applied to current data.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import exclusion list:\n{e}")

    def clear_exclusion(self):
        self.exclusion_list.clear()
        self.apply_filters()
        self.statusbar.showMessage("Exclusion list cleared.")

    # --- Summary ---
    def show_summary(self):
        summary = defaultdict(lambda: {"ERROR":0, "FATAL":0, "WARNING":0})
        unique_msgs = defaultdict(lambda: {"ERROR": set(), "FATAL": set(), "WARNING": set()})
        excluded_counts = defaultdict(lambda: {"ERROR":0, "FATAL":0, "WARNING":0})
        log_types = defaultdict(set)
    
        # Only process rows with non-empty Test Case and Test Option
        for row in self.filtered_rows:
            testcase = row[1]
            testopt = row[2]
            if not testcase or not testopt:
                continue
            typ = row[3]
            count = int(row[4])
            msg = row[5]
            log_type = row[6]  # "simulate" or "compile"
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
        unique_rows = len({tuple(row) for row in self.filtered_rows})
        stats = self.get_message_stats()
        msg = (f"Showing {row_count} rows | Unique rows: {unique_rows} | "
               f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
               f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
               f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)")
        self.statusbar.showMessage(msg)

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
        row_key = tuple(self.table.item(row, col).text() for col in range(len(self.columns) - 1))
        comment = self.comments_dict.get(row_key, "")
        msg = comment if comment.strip() else "(No comments)"
        QMessageBox.information(self, "All Comments", msg)

    def show_shortcuts(self):
        QMessageBox.information(self, "Shortcut Keys",
            "File Menu:\n"
            "  Ctrl+O: Load Log Folder\n"
            "  Ctrl+R: Reload\n"
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

    def toggle_column(self, col_index, checked):
        self.table.setColumnHidden(col_index, not checked)
        self.update_filter_row_geometry()

    def open_log_file(self, index):
        row = index.row()
        filepath = self.table.item(row, 7).text()
        if os.path.isfile(filepath):
            os.system(f"gvim '{filepath}' &")
        else:
            QMessageBox.warning(self, "Open Log File", f"File not found:\n{filepath}")

    def handle_table_double_click(self, index):
        if index.column() == len(self.columns) - 1:  # Comments column
            # Open dialog for multi-line editing
            current_text = self.table.item(index.row(), index.column()).text()
            dlg = CommentEditDialog(current_text, self)
            if dlg.exec_() == QDialog.Accepted:
                new_text = dlg.get_text()
                self.table.item(index.row(), index.column()).setText(new_text)
                # Update comments_dict
                row_key = tuple(self.table.item(index.row(), col).text() for col in range(len(self.columns) - 1))
                self.comments_dict[row_key] = new_text
        else:
            self.open_log_file(index)

    # --- Log menu actions ---
    def toggle_simulate(self):
        self.show_simulate = self.simulate_action.isChecked()
        self.load_log_folder(self.loaded_folder)

    def toggle_compile(self):
        self.show_compile = self.compile_action.isChecked()
        self.load_log_folder(self.loaded_folder)

    def toggle_scoreboard(self):
        self.show_scoreboard = self.scoreboard_action.isChecked()
        self.apply_filters()

    def save_session(self):
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
                    writer.writerow(row)
                f.write("[COMMENTS]\n")
                for key, comment in self.comments_dict.items():
                    writer.writerow(list(key) + [comment])
                f.write("[EXCLUSIONS]\n")
                for msg in self.exclusion_list:
                    writer.writerow([msg])
            self.statusbar.showMessage(f"Session saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Session Error", f"Failed to save session:\n{e}")

    def update_comments_dict_from_table(self):
        comments_col = self.columns.index("Comments")
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(len(self.columns) - 1):
                cell = self.table.item(row, col)
                row_data.append(cell.text() if cell else "")
            row_key = tuple(row_data)
            comment_item = self.table.item(row, comments_col)
            comment = comment_item.text() if comment_item else ""
            self.comments_dict[row_key] = comment

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
                    rows.append(row)
                else:
                    section_header = None
    
                comments_dict = {}
                if section_header == "[COMMENTS]":
                    for row in csv.reader(f):
                        if row and row[0].startswith("["):
                            section_header = row[0]
                            break
                        if len(row) < len(self.columns) - 2:  # Excluded and Comments not in data
                            continue
                        row_key = tuple(row[:len(self.columns)-2])
                        comment = row[len(self.columns)-2]
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
            self.statusbar.showMessage(
                f"Session loaded from {path} | Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
                f"ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique), "
                f"FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique), "
                f"WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)"
            )
    
            self.progress.setMaximum(1)
            self.progress.setValue(1)
            self.progress.setFormat("Session loaded.")
            QApplication.processEvents()
        except Exception as e:
            self.progress.setFormat("Failed to load session.")
            QMessageBox.critical(self, "Load Session Error", f"Failed to load session:\n{e}")

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

    def __init__(self, log_files, show_simulate, show_compile, show_scoreboard):
        super().__init__()
        self.memory_warning_threshold_mb = 500  # You can make this configurable via a settings dialog
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
                    id_val, testcase, testopt, "ERROR", count, msg, "simulate" if "simulate" in os.path.basename(filepath) else "compile", filepath
                ]
                all_rows.append(row)
            for msg, count in fatal_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = [
                    id_val, testcase, testopt, "FATAL", count, msg, "simulate" if "simulate" in os.path.basename(filepath) else "compile", filepath
                ]
                all_rows.append(row)
            for msg, count in warning_counts.items():
                if not self.show_scoreboard and "sbd_compare" in msg.lower():
                    continue
                row = [
                    id_val, testcase, testopt, "WARNING", count, msg, "simulate" if "simulate" in os.path.basename(filepath) else "compile", filepath
                ]
                all_rows.append(row)
            self.progress.emit(idx+1, len(self.log_files))
        self.finished.emit(all_rows)

if __name__ == "__main__":
    logging.basicConfig(
        filename='tool_error.log',
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s'
    )

    def log_uncaught_exceptions(exctype, value, tb):
        error_msg = "".join(traceback.format_exception(exctype, value, tb))
        logging.error("Uncaught exception:\n%s", error_msg)
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Unexpected Error",
            "An unexpected error occurred:\n\n" + str(value) +
            "\n\nSee tool_error.log for details.")

    sys.excepthook = log_uncaught_exceptions

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = LogTriageWindow()
    win.show()
    sys.exit(app.exec_())
