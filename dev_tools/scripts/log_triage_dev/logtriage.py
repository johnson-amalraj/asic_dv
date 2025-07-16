import sys
import os
import json
import gzip
import re
import logging
import traceback
import psutil
import matplotlib
import matplotlib.style
import numpy as np
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, 
    QWidget, QHBoxLayout, QLineEdit, QLabel, QProgressBar, QMenuBar, QMenu, QAction, 
    QMessageBox, QAbstractItemView, QHeaderView, QStatusBar, QDialog, QPushButton, 
    QInputDialog, QMenu, QTextEdit, QCheckBox, QComboBox, QGraphicsDropShadowEffect, QSizePolicy
)
from collections import Counter, defaultdict
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QSize
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from dataclasses import dataclass
from functools import partial
from PyQt5.QtGui import QColor

@dataclass
class LogRow:
    id: str
    testcase: str
    testopt: str
    type: str 
    count: int
    message: str         # cleaned message
    orig_message: str    # original message
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
    # msg = re.sub(r'\b\d+\b', 'N', msg) TODO Testing for this
    msg = re.sub(r'\s+', ' ', msg).strip()
    return msg

def open_log_file_anytype(filepath):
    if filepath.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
    else:
        return open(filepath, 'r', encoding='utf-8', errors='ignore')

def load_ignore_patterns_from_file(ignore_file):
    import json
    patterns = []
    try:
        if ignore_file.lower().endswith('.json'):
            with open(ignore_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Support both list of dicts and list of strings
                for entry in data:
                    if isinstance(entry, dict) and 'Regex' in entry:
                        patterns.append(re.compile(entry['Regex']))
                    elif isinstance(entry, str):
                        patterns.append(re.compile(entry))
        else:
            logger.error("Unsupported file format: %s", ignore_file)
            raise ValueError("Unsupported file format for ignore patterns. Only JSON is supported.")
    except FileNotFoundError:
        logger.error("Ignore patterns file not found: %s", ignore_file)
        raise FileNotFoundError(f"Ignore patterns file not found: {ignore_file}")
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in ignore patterns file: %s (%s)", ignore_file, e)
        raise ValueError(f"Invalid JSON in ignore patterns file: {ignore_file}\n{e}")
    except Exception as e:
        logger.error("Error loading ignore patterns file: %s (%s)", ignore_file, e)
        raise
    return patterns

def load_patterns_from_file(patterns_file):
    import json
    patterns = []
    try:
        if patterns_file.lower().endswith('.json'):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Support both list of dicts and list of (type, regex) tuples
                for entry in data:
                    if isinstance(entry, dict) and 'Type' in entry and 'Regex' in entry:
                        typ = entry['Type']
                        regex = re.compile(entry['Regex'])
                        patterns.append((typ, regex))
                    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                        typ, regex_str = entry
                        patterns.append((typ, re.compile(regex_str)))
        else:
            logger.error("Unsupported file format: %s", patterns_file)
            raise ValueError("Unsupported file format for regex patterns. Only JSON is supported.")
    except FileNotFoundError:
        logger.error("Regex patterns file not found: %s", patterns_file)
        raise FileNotFoundError(f"Regex patterns file not found: {patterns_file}")
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in regex patterns file: %s (%s)", patterns_file, e)
        raise ValueError(f"Invalid JSON in regex patterns file: {patterns_file}\n{e}")
    except Exception as e:
        logger.error("Error loading regex patterns file: %s (%s)", patterns_file, e)
        raise
    return patterns

def parse_log_file(filepath, patterns, ignore_patterns=None):
    logger.info(f"Start parsing: {filepath}")
    errors, fatals, warnings = [], [], []
    with open_log_file_anytype(filepath) as f:
        for lineno, line in enumerate(f, 1):
            line_stripped = line.strip()
            # Check ignore patterns first
            if ignore_patterns:
                if any(pat.search(line_stripped) for pat in ignore_patterns):
                    continue  # Skip this line/message

            for typ, pat in patterns:
                m = pat.search(line_stripped)
                if m:
                    start, end = m.span()
                    if start == 0:
                        msg = line_stripped[end:].lstrip(": \t")
                    else:
                        msg = line_stripped
                    msg_clean = clean_message(msg)
                    if typ == 'ERROR':
                        errors.append((msg_clean, msg, lineno))
                    elif typ == 'WARNING':
                        warnings.append((msg_clean, msg, lineno))
                    elif typ == 'FATAL':
                        fatals.append((msg_clean, msg, lineno))
                    break

    error_counts = Counter(errors)
    fatal_counts = Counter(fatals)
    warning_counts = Counter(warnings)
    return error_counts, fatal_counts, warning_counts
    logger.info(f"Finished parsing: {filepath}")

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
                "orig_message": row.orig_message,
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
        self.chart_combo.addItems(["Pie Chart", "Grouped Bar Chart"])
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
        matplotlib.style.use('dark_background' if dark else 'default')

    def update_chart(self):
        chart_type = self.chart_combo.currentText()
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        if chart_type == "Pie Chart":
            self.plot_pie(ax)
        elif chart_type == "Grouped Bar Chart":
            self.plot_bar(ax)
        self.canvas.draw()

    def plot_pie(self, ax):
        (stats, excluded_stats), _ = self.get_chart_data()
        labels = []
        sizes = []
        colors = ['#e74c3c', '#8e44ad', '#f1c40f']
        excluded_colors = ['#ffb3b3', '#dab6ff', '#fff7b3']  # lighter for excluded
        for i, typ in enumerate(["ERROR", "FATAL", "WARNING"]):
            if stats[typ] > 0:
                labels.append(f"{typ}: {stats[typ]})")
                sizes.append(stats[typ])
            if excluded_stats[typ] > 0:
                labels.append(f"{typ} (Excluded: {excluded_stats[typ]})")
                sizes.append(excluded_stats[typ])
        all_colors = []
        for i, typ in enumerate(["ERROR", "FATAL", "WARNING"]):
            if stats[typ] > 0:
                all_colors.append(colors[i])
            if excluded_stats[typ] > 0:
                all_colors.append(excluded_colors[i])
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=all_colors)
            ax.set_title("Distribution of Error Types")
        else:
            ax.text(0.5, 0.5, "No data", ha='center', va='center')

    def plot_bar(self, ax):
        _, bar_data = self.get_chart_data()
        testcases, data, excluded_data = bar_data['testcases'], bar_data['data'], bar_data['excluded_data']
        types = ["ERROR", "FATAL", "WARNING"]
        x = np.arange(len(testcases))
        width = 0.25
        colors = ['#e74c3c', '#8e44ad', '#f1c40f']
        excluded_colors = ['#ffb3b3', '#dab6ff', '#fff7b3']
        for i, typ in enumerate(types):
            included = [data[tc][typ] for tc in testcases]
            excluded = [excluded_data[tc][typ] for tc in testcases]
            ax.bar(x + i*width - width, included, width, label=f"{typ}", color=colors[i])
            ax.bar(x + i*width - width, excluded, width, bottom=included, label=f"{typ} (Excluded)", color=excluded_colors[i], hatch='//')
        ax.set_xticks(x)
        ax.set_xticklabels(testcases, rotation=45, ha='right')
        ax.set_ylabel("Count")
        ax.set_xlabel("Test Case")
        ax.set_title("Error/Fatal/Warning Counts by Test Case")
        ax.legend()
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

class HelpDialog(QDialog):
    def __init__(self, title, html, parent=None):
        super().__init__(parent)
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.gray)
        self.setGraphicsEffect(shadow)

        self.setWindowTitle(title)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setHtml(html)
        layout.addWidget(self.text_edit)

        btn = QPushButton("Close", self)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

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
        self.status_label = QLabel()
        self.statusbar.addWidget(self.status_label)
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
        export_btn = QPushButton("Export Summary to JSON", self)
        export_btn.clicked.connect(self.export_summary)
        layout.addWidget(export_btn)

    def apply_filters(self):
        self.update_comments_dict_from_table()
        filters = [edit.text().strip().lower() for edit in self.filters]
        self.filtered_rows = []
        for row in self.all_rows:
            # --- Debug print here ---
            logger.info(f"Row orig_message: {repr(getattr(row, 'orig_message', row.message))}")
            # ------------------------
            match = True
            for i, f in enumerate(filters):
                if f and f not in str(row[i]).lower():
                    match = False
                    break
            if match:
                self.filtered_rows.append(row)
    
        # --- Apply "Show First Match Per Testcase" filter if enabled ---
        if hasattr(self, 'show_first_match_action') and self.show_first_match_action.isChecked():
            first_matches = {}
            # You may need to adjust the key depending on your grouping needs
            for row in sorted(self.filtered_rows, key=lambda r: (r.testcase, r.testopt, r.logfilepath, r.type, r.linenumber)):
                key = (row.testcase, row.testopt, row.logfilepath, row.type)
                if key not in first_matches:
                    first_matches[key] = row
            self.filtered_rows = list(first_matches.values())
        # --------------------------------------------------------------
        self.populate_table(self.filtered_rows)

    def populate_table(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))

    def export_summary(self):
        import json
        try:
            default_dir = os.getcwd()
            path, _ = QFileDialog.getSaveFileName(self, "Export Summary to JSON", default_dir, "JSON Files (*.json)")
            if not path:
                return
            path = path.strip()
            # Prepare data: list of dicts, each dict is a row with column names as keys
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            data = []
            for i in range(self.table.rowCount()):
                row = {headers[j]: self.table.item(i, j).text() for j in range(self.table.columnCount())}
                data.append(row)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
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
        self.result = None  # Will be 'row', 'all', or None

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)

        btns = QHBoxLayout()
        self.row_btn = QPushButton("Apply to ROW", self)
        self.row_btn.clicked.connect(self.apply_row)
        btns.addWidget(self.row_btn)

        self.all_btn = QPushButton("Apply to ALL (message)", self)
        self.all_btn.clicked.connect(self.apply_all)
        btns.addWidget(self.all_btn)

        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        layout.addLayout(btns)

    def get_text(self):
        return self.text_edit.toPlainText()

    def apply_row(self):
        self.result = 'row'
        self.accept()

    def apply_all(self):
        self.result = 'all'
        self.accept()

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        try:
            self.value = int(value)
        except Exception:
            self.value = 0
    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)

class LogTriageWindow(QMainWindow):

    dark_stylesheet = """
    QWidget {
        background-color: #232629;
        color: #F0F0F0;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
        font-size: 10pt;
    }
    QTableWidget {
        background-color: #262b33;
        color: #F0F0F0;
        gridline-color: #444;
        selection-background-color: #00b4d8;
        selection-color: #fff;
        border-radius: 8px;
        alternate-background-color: #232629;
    }
    QHeaderView::section {
        background-color: #31363b;
        color: #F0F0F0;
        border: 1px solid #444;
        font-weight: bold;
        border-radius: 8px;
    }
    QLineEdit, QTextEdit {
        background-color: #31363b;
        color: #F0F0F0;
        border: 1px solid #444;
        selection-background-color: #ffe082;
        selection-color: #232629;
        border-radius: 8px;
    }
    QPushButton {
        border: none;
        padding: 8px 16px;
        background-color: #0078d7;
        color: #fff;
        font-weight: 500;
        transition: background 0.2s;
        border-radius: 8px;
    }
    QPushButton:hover {
        background-color: #005fa3;
        color: #ffffff;
    }
    QCheckBox, QComboBox {
        background-color: #31363b;
        color: #F0F0F0;
        border: 1px solid #444;
        border-radius: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #31363b;
        color: #F0F0F0;
        selection-background-color: #2d89ef;
        border-radius: 8px;
    }
    QMenuBar, QMenu {
        background-color: #232629;
        color: #F0F0F0;
    }
    QMenuBar::item:selected, QMenu::item:selected {
        background: #00b4d8;
        color: #fff;
        border-radius: 4px;
    }
    QMenuBar::item:pressed, QMenu::item:pressed {
        background: #005fa3;
        color: #fff;
        border-radius: 4px;
    }
    QWidget#filter_row_widget {
        background: #31363b;
        color: #F0F0F0;
        border-bottom: 1px solid #444;
        border-top: none;
        border-left: none;
        border-right: none;
        padding: 0px;
    }
    QLineEdit[filter="true"] {
        background: #31363b;
        color: #F0F0F0;
        border: 1px solid #444;
        border-radius: 0px;
        padding: 2px 4px;
        font-weight: normal;
    }
    """

    light_stylesheet = """
    QWidget {
        background-color: #f5f6fa;
        color: #232629;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
        font-size: 10pt;
    }
    QTableWidget {
        background-color: #ffffff;
        color: #232629;
        gridline-color: #d3d3d3;
        selection-background-color: #00b4d8;
        selection-color: #fff;
        border-radius: 8px;
        alternate-background-color: #f0f2f5;
    }
    QHeaderView::section {
        background-color: #e1e4ea;
        color: #232629;
        border: 1px solid #d3d3d3;
        font-weight: bold;
        border-radius: 8px;
    }
    QLineEdit, QTextEdit {
        background-color: #ffffff;
        color: #232629;
        border: 1px solid #b0b0b0;
        selection-background-color: #ffe082;
        selection-color: #232629;
        border-radius: 8px;
    }
    QMenuBar, QMenu {
        background-color: #f5f6fa;
        color: #232629;
    }
    QMenuBar::item:selected, QMenu::item:selected {
        background: #00b4d8;
        color: #fff;
        border-radius: 4px;
    }
    QMenuBar::item:pressed, QMenu::item:pressed {
        background: #005fa3;
        color: #fff;
        border-radius: 4px;
    }
    QStatusBar {
        background-color: #f5f6fa;
        color: #232629;
    }
    QLabel {
        color: #232629;
        background: transparent;
    }
    QProgressBar {
        background-color: #e1e4ea;
        color: #232629;
        border: 1px solid #b0b0b0;
        border-radius: 8px;
    }
    QProgressBar::chunk {
        background-color: #00b4d8;
        border-radius: 8px;
    }
    QPushButton {
        border: none;
        padding: 8px 16px;
        background-color: #0078d7;
        color: #fff;
        font-weight: 500;
        transition: background 0.2s;
        border-radius: 8px;
    }
    QPushButton:hover {
        background-color: #005fa3;
        color: #fff;
    }
    QCheckBox, QComboBox {
        background-color: #ffffff;
        color: #232629;
        border: 1px solid #b0b0b0;
        border-radius: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #232629;
        selection-background-color: #2d89ef;
        border-radius: 8px;
    }
    QWidget#filter_row_widget {
        background: #e1e4ea;
        color: #232629;
        border-bottom: 1px solid #d3d3d3;
        border-top: none;
        border-left: none;
        border-right: none;
        padding: 0px;
    }
    QLineEdit[filter="true"] {
        background: #e1e4ea;
        color: #232629;
        border: 1px solid #b0b0b0;
        border-radius: 0px;
        padding: 2px 4px;
        font-weight: normal;
    }
    """

    @staticmethod
    def is_night_time():
        now = datetime.datetime.now().time()
        return now >= datetime.time(19, 0) or now < datetime.time(7, 0)

    def __init__(self):
        super().__init__()
        self.patterns_file = os.path.join(os.path.dirname(__file__), "pattern/regex_patterns.json")
        logger.info(f"Loading {self.patterns_file} for regex pattern search...")
        self.ignore_patterns_file = os.path.join(os.path.dirname(__file__), "pattern/ignore_patterns.json")
        logger.info(f"Loading {self.ignore_patterns_file} for ignore pattern...")
        self.patterns = load_patterns_from_file(self.patterns_file)
        self.ignore_patterns = load_ignore_patterns_from_file(self.ignore_patterns_file)
        self.is_loading = False
        self.stop_requested = False
        self.exclusion_row_keys = set()
        self.comments_dict = {}  # {row_key: comment}
        self.setWindowTitle("Log Triage v4.1.0")
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
        # Automatically enable dark mode based on time
        if self.is_night_time():
            self.dark_mode_action.setChecked(True)
            self.setStyleSheet(self.dark_stylesheet)
        else:
            self.dark_mode_action.setChecked(False)
            self.setStyleSheet(self.light_stylesheet)
        self.restore_settings()
        self.setStyleSheet(self.light_stylesheet)
        self.exclusion_list = set()
        self.show_only_excluded = False
        self.show_only_nonexcluded = False
        self.show_only_commented = False
        self.show_only_noncommented = False

    def init_ui(self):
        central = QWidget()
        vbox = QVBoxLayout(central)
        self.setCentralWidget(central)
    
        # --- Add drop shadow to the central widget ---
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.gray)
        central.setGraphicsEffect(shadow)
        # --------------------------------------------
    
        # Table
        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow user to resize columns
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.handle_table_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow row header resizing
        self.table.verticalHeader().setDefaultSectionSize(30)  # Optional: set default row header width
        self.table.itemChanged.connect(self.handle_comment_edit)
        self.table.itemSelectionChanged.connect(self.update_selection_status)
        self.table.setAlternatingRowColors(True)
    
        # --- Set default column widths (customize as needed) ---
        # After setting headers and populating data:
        self.default_colwidths = [80, 180, 200, 80, 60, 450, 100, 450, 100, 100, 180]
        for i, w in enumerate(self.default_colwidths):
            self.table.setColumnWidth(i, w)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    
        # --- Filter row widget with row header label ---
        self.filter_row_widget = QWidget()
        self.filter_row_widget.setObjectName("filter_row_widget")
        filter_layout = QHBoxLayout(self.filter_row_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.row_header_label = QLabel("")
        self.row_header_label.setFixedWidth(self.table.verticalHeader().width())
        filter_layout.addWidget(self.row_header_label)
        
        self.filter_edits = []
        for i, col in enumerate(self.columns):
            edit = QLineEdit()
            edit.setPlaceholderText(f"Filter {col}")
            edit.setProperty("filter", True)  # <-- This enables the special styling in the stylesheet
            edit.textChanged.connect(self.apply_filters)
            edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            filter_layout.addWidget(edit)
            self.filter_edits.append(edit)

        vbox.addWidget(self.filter_row_widget)
        vbox.addWidget(self.table)
    
        # --- Keep row header label in sync with table's vertical header width ---
        self.table.verticalHeader().sectionResized.connect(lambda idx, old, new: self.sync_row_header_label())
        self.table.verticalHeader().geometriesChanged.connect(self.sync_row_header_label)  # Handles some edge cases
    
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
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_loading)
        vbox.addWidget(self.stop_btn)
    
        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
    
        # Menu bar
        self.menu = self.menuBar()
        self.init_menus()
    
    def get_current_stylesheet(self):
        return self.dark_stylesheet if self.dark_mode_action.isChecked() else self.light_stylesheet

    def sync_row_header_label(self):
        # Keep the filter row's row header label width in sync with the table's vertical header
        self.row_header_label.setFixedWidth(self.table.verticalHeader().width())

    def commit_active_editor(self):
        """If a cell editor is open, commit its data before refreshing the table."""
        if self.table.state() == QAbstractItemView.EditingState:
            self.table.closePersistentEditor(self.table.currentItem())
            self.table.clearFocus()
            QApplication.processEvents()

    def load_regex_patterns_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Regex Patterns File",
            os.getcwd(),
            "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            self.patterns = load_patterns_from_file(path)
            self.patterns_file = path
            QMessageBox.information(self, "Patterns Loaded", f"Patterns loaded from {path}")
            self.statusbar.showMessage(f"Patterns loaded from {path}.")
            logger.info(f"Patterns loaded from {path}.")
            # Prompt to reload
            if self.loaded_folder:
                reply = QMessageBox.question(
                    self, "Reload Logs?",
                    "Regex pattern file loaded. Do you want to reload the current log folder with the new patterns?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.load_log_folder(self.loaded_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load patterns file:\n{e}")
            logger.error(f"Failed to load patterns file: {e}")

    def load_ignore_patterns_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Ignore Patterns File",
            os.getcwd(),
            "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            self.ignore_patterns = load_ignore_patterns_from_file(path)
            self.ignore_patterns_file = path
            QMessageBox.information(self, "Ignore Patterns Loaded", f"Ignore patterns loaded from {path}")
            self.statusbar.showMessage(f"Ignore patterns loaded from {path}.")
            logger.info(f"Ignore patterns loaded from {path}.")
            # Automatically reload if a folder is loaded
            if self.loaded_folder:
                self.load_log_folder(self.loaded_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ignore patterns file:\n{e}")
            logger.error(f"Failed to load ignore patterns file: {e}")

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

    def clear_comment_selected(self, per_row=True):
        selected_rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        if not selected_rows:
            QMessageBox.warning(self, "Clear Comment", "No rows selected.")
            return
        if not per_row and len(selected_rows) > 1:
            QMessageBox.warning(self, "Clear Comment", "Please select only one row for [ALL] comment clearing.")
            return
        for visual_row in selected_rows:
            row_key = self.table.item(visual_row, 0).data(Qt.UserRole)
            logrow = next((r for r in self.filtered_rows if self.get_row_key(r) == row_key), None)
            if logrow is not None:
                if per_row:
                    # Remove comment for this row only
                    if row_key in self.comments_dict:
                        self.comments_dict.pop(row_key)
                else:
                    # Remove comment for all rows with the same orig_message
                    for r in self.all_rows:
                        if r.orig_message == logrow.orig_message:
                            k = self.get_row_key(r)
                            if k in self.comments_dict:
                                self.comments_dict.pop(k)
        self.update_table()
        self.statusbar.showMessage("Comment(s) cleared.")
        logger.info("Comment(s) cleared.")

    def toggle_show_only_commented(self):
        self.show_only_commented = self.show_only_commented_action.isChecked()
        if self.show_only_commented:
            self.show_only_noncommented = False
            self.show_only_noncommented_action.setChecked(False)
        self.apply_filters()
    
    def toggle_show_only_noncommented(self):
        self.show_only_noncommented = self.show_only_noncommented_action.isChecked()
        if self.show_only_noncommented:
            self.show_only_commented = False
            self.show_only_commented_action.setChecked(False)
        self.apply_filters()

    def update_selection_status(self):
        selected_rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        self.statusbar.showMessage(f"{len(selected_rows)} row(s) selected.")
        logger.info(f"{len(selected_rows)} row(s) selected.")

    def show_visualization_dialog(self):
        dlg = VisualizationDialog(self, self.get_visualization_data, self.dark_mode_action.isChecked())
        dlg.setStyleSheet(self.get_current_stylesheet())  # <-- Add this line
        dlg.exec_()

    def get_visualization_data(self):
        # Pie chart data
        stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
        excluded_stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
        for row in self.filtered_rows:
            if row.type in stats:
                is_excluded = (
                    getattr(row, 'orig_message', row.message) in self.exclusion_list or
                    self.get_row_key(row) in getattr(self, 'exclusion_row_keys', set())
                )
                if is_excluded:
                    excluded_stats[row.type] += int(row.count)
                else:
                    stats[row.type] += int(row.count)
        # Bar/heatmap data
        testcases = sorted({row.testcase for row in self.filtered_rows})
        types = ["ERROR", "FATAL", "WARNING"]
        data = {tc: {typ: 0 for typ in types} for tc in testcases}
        excluded_data = {tc: {typ: 0 for typ in types} for tc in testcases}
        for row in self.filtered_rows:
            tc = row.testcase
            typ = row.type
            is_excluded = (
                getattr(row, 'orig_message', row.message) in self.exclusion_list or
                self.get_row_key(row) in getattr(self, 'exclusion_row_keys', set())
            )
            if tc in data and typ in data[tc]:
                if is_excluded:
                    excluded_data[tc][typ] += int(row.count)
                else:
                    data[tc][typ] += int(row.count)
        return (stats, excluded_stats), {"testcases": testcases, "data": data, "excluded_data": excluded_data}

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
    
        recent_menu = QMenu("Recent Folders", self)
        self.recent_menu = recent_menu
        self.update_recent_menu()
        file_menu.addMenu(recent_menu)

        file_menu.addSeparator()

        save_session_action = QAction("Save Session", self)
        save_session_action.setShortcut("Ctrl+Shift+S")
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)
    
        load_session_action = QAction("Load Session", self)
        load_session_action.setShortcut("Ctrl+Shift+O")
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)
    
        file_menu.addSeparator()

        self.load_patterns_action = QAction("Load Regex Patterns File...", self)
        self.load_patterns_action.setShortcut("Ctrl+P")
        self.load_patterns_action.triggered.connect(self.load_regex_patterns_file)
        file_menu.addAction(self.load_patterns_action)

        self.load_ignore_patterns_action = QAction("Load Ignore Patterns File...", self)
        self.load_ignore_patterns_action.setShortcut("Ctrl+I")
        self.load_ignore_patterns_action.triggered.connect(self.load_ignore_patterns_file)
        file_menu.addAction(self.load_ignore_patterns_action)

        file_menu.addSeparator()

        reload_action = QAction("Reload", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_last_folder)
        file_menu.addAction(reload_action)

        file_menu.addSeparator()

        export_action = QAction("Export to JSON", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_to_json)
        file_menu.addAction(export_action)
    
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
        
        # Exclude [ROW]
        exclude_row_action = QAction("Exclude [This ROW only]", self)
        exclude_row_action.setShortcut("Ctrl+X")
        exclude_row_action.triggered.connect(lambda: self.add_to_exclusion(per_row=True))
        exclusion_menu.addAction(exclude_row_action)
        
        # Exclude [ALL]
        exclude_all_action = QAction("Exclude [ALL ROW with this message]", self)
        exclude_all_action.setShortcut("Ctrl+U")
        exclude_all_action.triggered.connect(lambda: self.add_to_exclusion(per_row=False))
        exclusion_menu.addAction(exclude_all_action)
        
        exclusion_menu.addSeparator()

        view_excl_action = QAction("View Exclusion List", self)
        view_excl_action.setShortcut("Ctrl+Shift+V")
        view_excl_action.triggered.connect(self.view_exclusion)
        exclusion_menu.addAction(view_excl_action)
    
        import_excl_action = QAction("Import Exclusion List", self)
        import_excl_action.setShortcut("Ctrl+Shift+I")
        import_excl_action.triggered.connect(self.import_exclusion_list)
        exclusion_menu.addAction(import_excl_action)
    
        export_excl_action = QAction("Export Exclusion List", self)
        export_excl_action.setShortcut("Ctrl+Shift+E")
        export_excl_action.triggered.connect(self.export_exclusion_list)
        exclusion_menu.addAction(export_excl_action)
    
        exclusion_menu.addSeparator()

        clear_excl_action = QAction("Clear Exclusion List", self)
        clear_excl_action.setShortcut("Ctrl+Shift+C")
        clear_excl_action.triggered.connect(self.clear_exclusion)
        exclusion_menu.addAction(clear_excl_action)
    
        clear_row_excl_action = QAction("Clear Per-Row Exclusions", self)
        clear_row_excl_action.setShortcut("Ctrl+Alt+R")
        clear_row_excl_action.triggered.connect(self.clear_per_row_exclusions)
        exclusion_menu.addAction(clear_row_excl_action)
        
        clear_msg_excl_action = QAction("Clear Per-Message Exclusions", self)
        clear_msg_excl_action.setShortcut("Ctrl+Alt+M")
        clear_msg_excl_action.triggered.connect(self.clear_per_message_exclusions)
        exclusion_menu.addAction(clear_msg_excl_action)

        exclusion_menu.addSeparator()

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
    
        # --- Comments clear actions ---
        comment_menu = self.menu.addMenu("&Comment")
        
        show_all_comments_action = QAction("Show All Comments", self)
        show_all_comments_action.setShortcut("Ctrl+Shift+M")
        show_all_comments_action.triggered.connect(self.show_all_comments)
        comment_menu.addAction(show_all_comments_action)
        
        comment_menu.addSeparator()
        
        clear_all_comments_action = QAction("Clear All Comments", self)
        clear_all_comments_action.setShortcut("Ctrl+Shift+Del")
        clear_all_comments_action.triggered.connect(self.clear_all_comments)
        comment_menu.addAction(clear_all_comments_action)
        
        clear_comment_row_action = QAction("Clear Comment [ROW]", self)
        clear_comment_row_action.setShortcut("Ctrl+Shift+R")
        clear_comment_row_action.triggered.connect(lambda: self.clear_comment_selected(per_row=True))
        comment_menu.addAction(clear_comment_row_action)
        
        clear_comment_all_action = QAction("Clear Comment [ALL ROW with this message]", self)
        clear_comment_all_action.setShortcut("Ctrl+Shift+G")
        clear_comment_all_action.triggered.connect(lambda: self.clear_comment_selected(per_row=False))
        comment_menu.addAction(clear_comment_all_action)
        
        comment_menu.addSeparator()
        
        self.show_only_commented_action = QAction("Show Only Commented Rows", self, checkable=True)
        self.show_only_commented_action.setShortcut("Ctrl+Alt+M")
        self.show_only_commented_action.setChecked(False)
        self.show_only_commented_action.triggered.connect(self.toggle_show_only_commented)
        comment_menu.addAction(self.show_only_commented_action)
        
        self.show_only_noncommented_action = QAction("Show Only Non-Commented Rows", self, checkable=True)
        self.show_only_noncommented_action.setShortcut("Ctrl+Alt+N")
        self.show_only_noncommented_action.setChecked(False)
        self.show_only_noncommented_action.triggered.connect(self.toggle_show_only_noncommented)
        comment_menu.addAction(self.show_only_noncommented_action)

        # Summary menu
        summary_menu = self.menu.addMenu("&Summary")

        show_summary_action = QAction("Show Summary", self)
        show_summary_action.setShortcut("Ctrl+S")
        show_summary_action.triggered.connect(self.show_summary)
        summary_menu.addAction(show_summary_action)
        
        show_row_stats_action = QAction("Show Row Stats", self)
        show_row_stats_action.setShortcut("Ctrl+Shift+R")
        show_row_stats_action.triggered.connect(self.show_row_stats)
        summary_menu.addAction(show_row_stats_action)

        summary_menu.addSeparator()

        self.show_all_rows_action = QAction("Show All Messages", self, checkable=True)
        self.show_all_rows_action.setShortcut("Ctrl+Shift+A")
        self.show_all_rows_action.setChecked(True)  # Default ON
        self.show_all_rows_action.triggered.connect(self.toggle_show_all_rows)
        summary_menu.addAction(self.show_all_rows_action)
        
        self.show_first_match_action = QAction("Show First Match Per Testcase", self, checkable=True)
        self.show_first_match_action.setShortcut("Ctrl+Shift+F")
        self.show_first_match_action.setChecked(False)
        self.show_first_match_action.triggered.connect(self.toggle_show_first_match)
        summary_menu.addAction(self.show_first_match_action)

        summary_menu.addSeparator()

        visualize_action = QAction("Open Visualization Window", self)
        visualize_action.setShortcut("Ctrl+T")
        visualize_action.triggered.connect(self.show_visualization_dialog)
        summary_menu.addAction(visualize_action)

        # Settings menu
        settings_menu = self.menu.addMenu("&Settings")

        self.dark_mode_action = QAction("Dark Mode", self, checkable=True)
        self.dark_mode_action.setShortcut("Ctrl+D")
        self.dark_mode_action.setChecked(False)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        settings_menu.addAction(self.dark_mode_action)
    
        # Help menu
        help_menu = self.menu.addMenu("&Help")

        shortcut_action = QAction("Shortcut Keys", self)
        shortcut_action.setShortcut("F1")
        shortcut_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcut_action)
    
        help_menu.addSeparator()

        features_action = QAction("Features", self)
        features_action.setShortcut("F2")
        features_action.triggered.connect(self.show_features)
        help_menu.addAction(features_action)
    
        help_menu.addSeparator()

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
        self.stop_btn.setVisible(loading)  # <-- Add this line
        self.menu.setEnabled(not loading)

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
    
        self.folder_status_label.setText(f"Loading log file folder path: {folder} ...")
        logger.info(f"Loading log file folder path: {folder} ...")
    
        self.stop_requested = False
        self.worker = LogParseWorker(log_files, self.show_simulate, self.show_compile, self.show_scoreboard, self.patterns, self.ignore_patterns)

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
            self.folder_status_label.setText(f"Loading stopped by user. Partial results showing.")
            logger.info(f"Loading stopped by user. Partial results showing.")
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
                    is_excluded = (
                        getattr(row, 'orig_message', row.message) in self.exclusion_list or
                        self.get_row_key(row) in getattr(self, 'exclusion_row_keys', set())
                    )
                    if (f in ["yes", "y", "1", "true"] and not is_excluded) or (f in ["no", "n", "0", "false"] and is_excluded):
                        match = False
                        break
                    if f not in ["yes", "y", "1", "true", "no", "n", "0", "false"]:
                        if (f not in ("yes" if is_excluded else "no")):
                            match = False
                            break
                elif col_name == "Comments":
                    continue
                else:
                    attr = self._colname_to_attr(col_name)
                    if not self.match_advanced_filter(str(getattr(row, attr)), f):
                        match = False
                        break
            if not match:
                continue
    
            # --- Exclusion filter logic (NEW) ---
            is_excluded = (
                getattr(row, 'orig_message', row.message) in self.exclusion_list or
                self.get_row_key(row) in getattr(self, 'exclusion_row_keys', set())
            )
            if self.show_only_excluded and not is_excluded:
                continue
            if self.show_only_nonexcluded and is_excluded:
                continue
            # -------------------------------------
    
            # --- Comment filter logic (NEW) ---
            row_key = self.get_row_key(row)
            has_comment = bool(self.comments_dict.get(row_key, "").strip())
            if getattr(self, 'show_only_commented', False) and not has_comment:
                continue
            if getattr(self, 'show_only_noncommented', False) and has_comment:
                continue
            # ----------------------------------
    
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
        for i, row in enumerate(self.filtered_rows):  # <--- Outer loop over rows
            row_key = self.get_row_key(row)
            excluded_by_message = getattr(row, 'orig_message', row.message) in self.exclusion_list
            excluded_by_row = row_key in getattr(self, 'exclusion_row_keys', set())
            is_excluded = excluded_by_message or excluded_by_row
            for j, col in enumerate(self.columns):  # <--- Inner loop over columns
                if col == "Excluded":
                    if excluded_by_row:
                        item = QTableWidgetItem("Yes (Row)")
                        item.setToolTip("Excluded: This row only")
                    elif excluded_by_message:
                        item = QTableWidgetItem("Yes (Msg)")
                        item.setToolTip("Excluded: All rows with this message")
                    else:
                        item = QTableWidgetItem("No")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                elif col == "Comments":
                    comment = self.comments_dict.get(row_key, "")
                    item = QTableWidgetItem(comment)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    attr = self._colname_to_attr(col)
                    value = getattr(row, attr)
                    if col == "Count":
                        item = NumericTableWidgetItem(value)
                    else:
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
                    if attr in ["testopt", "message", "logfilepath"]:
                        item.setToolTip(str(value))
                # --- Exclusion coloring ---
                if is_excluded:
                    if excluded_by_row:
                        # Per-row exclusion: light grey
                        item.setBackground(QColor("#d3d3d3"))  # light grey, works for both themes
                    elif excluded_by_message:
                        # Per-message exclusion: dark grey
                        item.setBackground(QColor("#a9a9a9"))  # dark grey, works for both themes
                self.table.setItem(i, j, item)
        self.table.setColumnHidden(7, False)

    def update_table(self, sort=True):
        self.table.setSortingEnabled(False)
        self.populate_table_rows()
        # Set column widths again here
        for i, w in enumerate(self.default_colwidths):
            self.table.setColumnWidth(i, w)
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
                    key.append(getattr(row, 'orig_message', row.message) in self.exclusion_list)
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
    def export_to_json(self):
        self.update_comments_dict_from_table()  # Ensure comments are up to date
    
        # Prepare data for export
        export_data = {
            "rows": [],
            "exclusion_list": list(self.exclusion_list),
            "exclusion_row_keys": [list(k) for k in self.exclusion_row_keys],  # Save as list of lists for JSON
            "comments": {str(k): v for k, v in self.comments_dict.items()}
        }

        for row in self.filtered_rows:
            row_key = (
                row.id, row.testcase, row.testopt, row.type,
                row.message, row.logtype, row.logfilepath, row.linenumber
            )
            excluded_by_row = row_key in getattr(self, 'exclusion_row_keys', set())
            excluded_by_message = getattr(row, 'orig_message', row.message) in self.exclusion_list
            is_excluded = excluded_by_row or excluded_by_message
        
            # Determine exclusion type
            if excluded_by_row:
                exclusion_type = "row"
            elif excluded_by_message:
                exclusion_type = "message"
            else:
                exclusion_type = "none"
        
            comment = self.comments_dict.get(row_key, "")
            export_data["rows"].append({
                "id": row.id,
                "testcase": row.testcase,
                "testopt": row.testopt,
                "type": row.type,
                "count": row.count,
                "message": row.message,
                "orig_message": row.orig_message,
                "logtype": row.logtype,
                "logfilepath": row.logfilepath,
                "linenumber": row.linenumber,
                "excluded": is_excluded,
                "exclusion_type": exclusion_type,   # <--- ADD THIS LINE
                "comment": comment
            })

        # Ask user for file path
        path, _ = QFileDialog.getSaveFileName(self, "Export to JSON", os.getcwd(), "JSON Files (*.json)")
        if not path or not path.strip():
            return
        path = path.strip()
    
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            self.statusbar.showMessage(f"Exported {len(export_data['rows'])} rows to {path}")
            logger.info(f"Exported {len(export_data['rows'])} rows to {path}")
            QMessageBox.information(self, "Export Info",
                f"Exported {len(export_data['rows'])} rows to {path}\n"
                f"Excluded rows in export: {sum(1 for r in export_data['rows'] if r['excluded'])}")
        except Exception as e:
            self.statusbar.showMessage(f"Failed to export: {e}")
            logger.error(f"Failed to export: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    def add_to_exclusion(self, per_row=True):
        self.commit_active_editor()
        self.update_comments_dict_from_table()
        selected_rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        if not selected_rows:
            QMessageBox.warning(self, "Exclusion", "No rows selected.")
            return
        if not per_row and len(selected_rows) > 1:
            QMessageBox.warning(self, "Exclusion", "Please select only one row for [ALL (msg)] exclusion.")
            return
        for visual_row in selected_rows:
            row_key = self.table.item(visual_row, 0).data(Qt.UserRole)
            logrow = next((r for r in self.filtered_rows if self.get_row_key(r) == row_key), None)
            if logrow is not None:
                if per_row:
                    row_key = self.get_row_key(logrow)
                    self.exclusion_row_keys.add(row_key)
                else:
                    self.exclusion_list.add(logrow.orig_message)
        logger.info("Exclusion list now contains:")
        for msg in self.exclusion_list:
            logger.info(repr(msg))
        self.apply_filters()
        self.statusbar.showMessage("Exclusion applied.")
        logger.info(f"Exclusion applied")

    def view_exclusion(self):
        # Prepare data for the table
        exclusion_data = []
        # Per-message exclusions
        for msg in sorted(self.exclusion_list):
            exclusion_data.append(("Message", msg))
        for row_key in sorted(self.exclusion_row_keys):
            # row_key: (id, testcase, testopt, type, message, logtype, logfilepath, linenumber)
            # Find the corresponding LogRow for display
            logrow = next((r for r in self.all_rows if self.get_row_key(r) == row_key), None)
            if logrow:
                summary = f"{logrow.message} | {logrow.logfilepath}:{logrow.linenumber}"
            else:
                summary = str(row_key)
            exclusion_data.append(("Row", summary))

        # Create dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Exclusion List")
        dlg.resize(800, 400)
        layout = QVBoxLayout(dlg)
    
        table = QTableWidget(len(exclusion_data), 2)
        table.setHorizontalHeaderLabels(["Exclusion Type", "Value"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, (excl_type, value) in enumerate(exclusion_data):
            table.setItem(i, 0, QTableWidgetItem(excl_type))
            table.setItem(i, 1, QTableWidgetItem(value))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(table)
    
        btn = QPushButton("Close", dlg)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
    
        dlg.exec_()

    def export_exclusion_list(self):
        self.update_comments_dict_from_table()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Exclusion List (JSON)", os.getcwd(), "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            exclusion_data = {
                "per_message": [],
                "per_row": []
            }
            # Per-message exclusions
            for msg in sorted(self.exclusion_list):
                comment = ""
                for logrow in self.all_rows:
                    if hasattr(logrow, 'orig_message') and logrow.orig_message == msg:
                        row_key = (
                            logrow.id, logrow.testcase, logrow.testopt, logrow.type,
                            logrow.message, logrow.logtype, logrow.logfilepath, logrow.linenumber
                        )
                        comment = self.comments_dict.get(row_key, "")
                        if comment:
                            break
                exclusion_data["per_message"].append({"message": msg, "comment": comment})
    
            # Per-row exclusions
            for row_key in sorted(self.exclusion_row_keys):
                # Find the corresponding LogRow for display and comment
                logrow = next((r for r in self.all_rows if self.get_row_key(r) == row_key), None)
                comment = self.comments_dict.get(row_key, "")
                exclusion_data["per_row"].append({
                    "row_key": list(row_key),
                    "comment": comment,
                    "summary": f"{logrow.message} | {logrow.logfilepath}:{logrow.linenumber}" if logrow else str(row_key)
                })
    
            with open(path, "w", encoding="utf-8") as f:
                json.dump(exclusion_data, f, indent=2, ensure_ascii=False)
            self.statusbar.showMessage(f"Exclusion list exported to {path}")
            logger.info(f"Exclusion list exported to {path}.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export exclusion list:\n{e}")
            logger.error(f"Export Error, Failed to export exclusion list:{e}")

    def import_exclusion_list(self):
        self.update_comments_dict_from_table()
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Exclusion List (JSON)", os.getcwd(), "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                exclusion_data = json.load(f)
                # Per-message exclusions
                for entry in exclusion_data.get("per_message", []):
                    msg = entry.get("message", "")
                    comment = entry.get("comment", "")
                    if not msg:
                        continue
                    self.exclusion_list.add(msg)
                    for logrow in self.all_rows:
                        if hasattr(logrow, 'orig_message') and logrow.orig_message == msg:
                            row_key = (
                                logrow.id, logrow.testcase, logrow.testopt, logrow.type,
                                logrow.message, logrow.logtype, logrow.logfilepath, logrow.linenumber
                            )
                            self.comments_dict[row_key] = comment
                # Per-row exclusions
                for entry in exclusion_data.get("per_row", []):
                    row_key = tuple(entry.get("row_key", []))
                    comment = entry.get("comment", "")
                    if row_key:
                        self.exclusion_row_keys.add(row_key)
                        self.comments_dict[row_key] = comment
            self.apply_filters()
            self.update_table()
            self.statusbar.showMessage(f"Exclusion list imported from {path} and applied to current data.")
            logger.info(f"Exclusion list imported from {path} and applied to current data.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import exclusion list:\n{e}")
            logger.error(f"Import Error, Failed to import exclusion list:{e}")

    def clear_exclusion(self):
        self.update_comments_dict_from_table()
        self.exclusion_list.clear()
        self.exclusion_row_keys.clear()  # <-- This is required!
        self.apply_filters()
        self.statusbar.showMessage("Exclusion list cleared.")
        logger.info(f"Exclusion list cleared.")

    def clear_per_row_exclusions(self):
        self.exclusion_row_keys.clear()
        self.apply_filters()
        self.statusbar.showMessage("Per-row exclusions cleared.")
        logger.info(f"Per-row exclusions cleared.")
    
    def clear_per_message_exclusions(self):
        self.exclusion_list.clear()
        self.apply_filters()
        self.statusbar.showMessage("Per-message exclusions cleared.")
        logger.info(f"Per-message exclusions cleared.")

    def clear_all_comments(self):
        self.comments_dict.clear()
        self.update_table()
        self.statusbar.showMessage("All comments cleared.")
        logger.info("All comments cleared.")
    
    def clear_per_row_comments(self):
        # Remove comments only for per-row exclusions
        keys_to_remove = set()
        for row_key in self.comments_dict:
            if row_key in self.exclusion_row_keys:
                keys_to_remove.add(row_key)
        for k in keys_to_remove:
            self.comments_dict.pop(k, None)
        self.update_table()
        self.statusbar.showMessage("Per-row comments cleared.")
        logger.info("Per-row comments cleared.")
    
    def clear_per_message_comments(self):
        # Remove comments for all rows whose orig_message is in exclusion_list
        keys_to_remove = set()
        for row in self.all_rows:
            if row.orig_message in self.exclusion_list:
                row_key = self.get_row_key(row)
                if row_key in self.comments_dict:
                    keys_to_remove.add(row_key)
        for k in keys_to_remove:
            self.comments_dict.pop(k, None)
        self.update_table()
        self.statusbar.showMessage("Per-message comments cleared.")
        logger.info("Per-message comments cleared.")

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
            msg = getattr(row, 'orig_message', row.message)
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

    def toggle_show_all_rows(self):
        if self.show_all_rows_action.isChecked():
            self.show_first_match_action.setChecked(False)
            self.apply_filters()  # Show all filtered rows
            self.statusbar.showMessage(f"Showing all filtered rows: {len(self.filtered_rows)} rows.")
            logger.info(f"Showing all filtered rows: {len(self.filtered_rows)} rows.")
        else:
            # Prevent unchecking both, always keep one checked
            self.show_all_rows_action.setChecked(True)
    
    def toggle_show_first_match(self):
        if self.show_first_match_action.isChecked():
            self.show_all_rows_action.setChecked(False)
            # Show only first match per testcase/logfile/type
            first_matches = {}
            for row in sorted(self.filtered_rows, key=lambda r: (r.testcase, r.testopt, r.logfilepath, r.type, r.linenumber)):
                key = (row.testcase, row.testopt, row.logfilepath, row.type)
                if key not in first_matches:
                    first_matches[key] = row
            self.filtered_rows = list(first_matches.values())
            self.update_table()
            self.statusbar.showMessage(f"Showing only first match per testcase/logfile/type: {len(self.filtered_rows)} rows.")
            logger.info(f"Showing only first match per testcase/logfile/type: {len(self.filtered_rows)} rows.")
        else:
            # Prevent unchecking both, always keep one checked
            self.show_first_match_action.setChecked(True)

    # --- Context Menu ---
    def show_context_menu(self, pos):
        menu = QMenu(self)
    
        copy_cell_action = QAction("Copy Cell", self)
        copy_cell_action.setShortcut("Ctrl+Shift+C")
        copy_cell_action.triggered.connect(self.copy_current_cell)
        menu.addAction(copy_cell_action)
    
        excl_row_action = QAction("Exclude [This ROW only]", self)
        excl_row_action.setShortcut("Ctrl+X")
        excl_row_action.triggered.connect(lambda: self.add_to_exclusion(per_row=True))
        menu.addAction(excl_row_action)
    
        excl_all_action = QAction("Exclude [ALL ROW with this message]", self)
        excl_all_action.setShortcut("Ctrl+U")
        excl_all_action.triggered.connect(lambda: self.add_to_exclusion(per_row=False))
        menu.addAction(excl_all_action)
    
        show_all_comments_action = QAction("Show All Comments", self)
        show_all_comments_action.setShortcut("Ctrl+Shift+M")
        show_all_comments_action.triggered.connect(self.show_all_comments)
        menu.addAction(show_all_comments_action)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def show_all_comments(self):
        # Prepare data for the table: only rows with a comment (non-empty)
        table_data = []
        for row in self.filtered_rows:
            row_key = self.get_row_key(row)
            comment = self.comments_dict.get(row_key, "")
            if comment.strip():  # Only show rows with a comment
                table_data.append([
                    str(row.id),
                    str(row.testcase),
                    comment.strip()
                ])
    
        if not table_data:
            QMessageBox.information(self, "All Comments", "No comments found in the current table.")
            return
    
        # Create dialog with a table
        dlg = QDialog(self)
        dlg.setWindowTitle("All Comments (Full Table)")
        dlg.resize(800, 400)
        layout = QVBoxLayout(dlg)
    
        table_widget = QTableWidget(len(table_data), 3)
        table_widget.setHorizontalHeaderLabels(["Test ID", "Test Name", "Comment"])
        table_widget.verticalHeader().setVisible(False)
        table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, (test_id, test_name, comment) in enumerate(table_data):
            table_widget.setItem(i, 0, QTableWidgetItem(test_id))
            table_widget.setItem(i, 1, QTableWidgetItem(test_name))
            table_widget.setItem(i, 2, QTableWidgetItem(comment))
        table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(table_widget)
    
        btn = QPushButton("Close", dlg)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
    
        dlg.exec_()

    def show_shortcuts(self):
        html = (
            "<h2>LogTriage Application – Keyboard Shortcuts</h2>"
            "<ul>"
            "<li><b>File Menu</b>"
            "<ul>"
            "<li><code>Ctrl+O</code>: Load Log Folder</li>"
            "<li><code>Ctrl+R</code>: Reload</li>"
            "<li><code>Ctrl+P</code>: Load Patterns File</li>"
            "<li><code>Ctrl+E</code>: Export to JSON</li>"
            "<li><code>Ctrl+Q</code>: Exit</li>"
            "</ul></li>"
    
            "<li><b>Edit Menu</b>"
            "<ul>"
            "<li><code>Ctrl+C</code>: Copy Selected Row(s)</li>"
            "<li><code>Ctrl+F</code>: Find</li>"
            "</ul></li>"
    
            "<li><b>Exclusion Menu</b>"
            "<ul>"
            "<li><code>Ctrl+X</code>: Exclude [This ROW only]</li>"
            "<li><code>Ctrl+U</code>: Exclude [ALL ROW with this message]</li>"
            "<li><code>Ctrl+Shift+V</code>: View Exclusion List</li>"
            "<li><code>Ctrl+Shift+E</code>: Export Exclusion List</li>"
            "<li><code>Ctrl+Shift+I</code>: Import Exclusion List</li>"
            "<li><code>Ctrl+Shift+C</code>: Clear Exclusion List</li>"
            "<li><code>Ctrl+Shift+X</code>: Show Only Excluded Rows</li>"
            "<li><code>Ctrl+Shift+N</code>: Show Only Non-Excluded Rows</li>"
            "<li><code>Ctrl+Alt+R</code>: Clear Per-Row Exclusions</li>"
            "<li><code>Ctrl+Alt+M</code>: Clear Per-Message Exclusions</li>"
            "</ul></li>"
    
            "<li><b>Comment Menu</b>"
            "<ul>"
            "<li><code>Ctrl+Shift+M</code>: Show All Comments</li>"
            "<li><code>Ctrl+Shift+Del</code>: Clear All Comments</li>"
            "<li><code>Ctrl+Shift+R</code>: Clear Comment [ROW]</li>"
            "<li><code>Ctrl+Shift+G</code>: Clear Comment [ALL ROW with this message]</li>"
            "<li><code>Ctrl+Alt+M</code>: Show Only Commented Rows</li>"
            "<li><code>Ctrl+Alt+N</code>: Show Only Non-Commented Rows</li>"
            "</ul></li>"
    
            "<li><b>Log Menu</b>"
            "<ul>"
            "<li><code>Ctrl+1</code>: Show simulate.log</li>"
            "<li><code>Ctrl+2</code>: Show compile.log</li>"
            "<li><code>Ctrl+3</code>: Show Scoreboard Errors</li>"
            "</ul></li>"
    
            "<li><b>Summary Menu</b>"
            "<ul>"
            "<li><code>Ctrl+S</code>: Show Summary</li>"
            "<li><code>Ctrl+Shift+R</code>: Show Row Stats</li>"
            "<li><code>Ctrl+Shift+A</code>: Show All Messages</li>"
            "<li><code>Ctrl+Shift+F</code>: Show First Match Per Testcase</li>"
            "<li><code>Ctrl+T</code>: Open Visualization Window</li>"
            "</ul></li>"
    
            "<li><b>Session Menu</b>"
            "<ul>"
            "<li><code>Ctrl+Shift+S</code>: Save Session</li>"
            "<li><code>Ctrl+Shift+O</code>: Load Session</li>"
            "</ul></li>"
    
            "<li><b>Settings Menu</b>"
            "<ul>"
            "<li><code>Ctrl+D</code>: Dark Mode</li>"
            "</ul></li>"
    
            "<li><b>Context Menu (Right-click on Table Row)</b>"
            "<ul>"
            "<li><code>Ctrl+Shift+C</code>: Copy Cell</li>"
            "<li><code>Ctrl+X</code>: Exclude [This ROW only]</li>"
            "<li><code>Ctrl+U</code>: Exclude [ALL ROW with this message]</li>"
            "<li><code>Ctrl+Shift+M</code>: Show All Comments</li>"
            "</ul></li>"
    
            "<li><b>Help Menu</b>"
            "<ul>"
            "<li><code>F1</code>: Shortcut Keys</li>"
            "<li><code>F2</code>: Features</li>"
            "<li><code>F3</code>: Author</li>"
            "</ul></li>"
    
            "<li><b>Other Table Actions</b>"
            "<ul>"
            "<li><b>Multi-column sort:</b> <code>Shift+Click</code> on header</li>"
            "<li><b>Filter columns:</b> Use filter row (no shortcut)</li>"
            "</ul></li>"
            "</ul>"
            "<p><b>Tip:</b> You can also use the context menu (right-click) for quick actions.</p>"
        )
        dlg = HelpDialog("Shortcut Keys", html, self)
        dlg.setStyleSheet(self.get_current_stylesheet())
        dlg.exec_()

    def show_features(self):
        html = (
            "<h2>LogTriage Application – Features</h2>"
            "<ol>"
            "<li><b>Log File Loading</b><ul>"
            "<li>Load and parse simulation/compile log files (<code>.log</code>, <code>.log.gz</code>) from folders, including recursive search.</li>"
            "<li>Supports both <code>simulate.log</code> and <code>compile.log</code> files.</li>"
            "<li>Progress bar and status messages during long operations.</li>"
            "<li>Recent folders menu for quick access.</li>"
            "</ul></li>"
            "<li><b>Tabular Log View</b><ul>"
            "<li>Display log messages in a table with columns: <i>ID, Test Case, Test Option, Type, Count, Message, Log Type, Log File Path, Excluded</i>.</li>"
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
            "<li>Add messages to an exclusion list (per-row or per-message) with keyboard shortcuts.</li>"
            "<li>View, import, export, and clear the exclusion list.</li>"
            "<li>Visual indication for excluded rows.</li>"
            "<li>Filter to show only excluded or only non-excluded rows.</li>"
            "<li>Clear per-row or per-message exclusions with shortcuts.</li>"
            "</ul></li>"
            "<li><b>Comment Management</b><ul>"
            "<li>Add, edit, and clear comments per-row or per-message.</li>"
            "<li>Show all comments in a dedicated dialog.</li>"
            "<li>Clear per-row or per-message comments with shortcuts.</li>"
            "</ul></li>"
            "<li><b>Summary and Statistics</b><ul>"
            "<li>Summary dialog: per-testcase/testopt counts for <b>ERROR</b>, <b>FATAL</b>, <b>WARNING</b> (total and unique).</li>"
            "<li>Quick menu option to display current filtered row count and unique count in the status bar.</li>"
            "</ul></li>"
            "<li><b>Visualization</b><ul>"
            "<li>Pie chart: Distribution of error types.</li>"
            "<li>Grouped bar chart: Error/Fatal/Warning counts by test case.</li>"
            "<li>Export all charts as images.</li>"
            "</ul></li>"
            "<li><b>User Interface and Usability</b><ul>"
            "<li>Dark mode toggle for comfortable viewing.</li>"
            "<li><b>Keyboard shortcuts for all major actions and context menus (see Help &gt; Shortcut Keys).</b></li>"
            "<li>Status bar shows current row count, unique count, and error statistics.</li>"
            "<li>Progress bar and status messages for long operations.</li>"
            "<li>Memory usage warning for large datasets.</li>"
            "</ul></li>"
            "<li><b>Robustness and Help</b><ul>"
            "<li>Robust error handling and logging (errors are logged to <code>tool_error.log</code>).</li>"
            "<li>Help menu with shortcut keys, features, and author info.</li>"
            "</ul></li>"
            "</ol>"
            "<p><b>Tip:</b> Right-click on any row to access context menu actions with shortcuts.</p>"
        )
        dlg = HelpDialog("Features", html, self)
        dlg.setStyleSheet(self.get_current_stylesheet())
        dlg.exec_()

    def show_author(self):
        html = (
            "LogTriage Application<br>"
            "Author: Johnson Amalraj (I77655) with help of <a href='https://chatbot/'>https://chatbot/</a><br>"
            "Contact: johnson.amalraj@microchip.com"
        )
        dlg = HelpDialog("Author", html, self)
        dlg.setStyleSheet(self.get_current_stylesheet())  # <-- Add this line
        dlg.exec_()

    def copy_selected_rows(self):
        selected_rows = set(index.row() for index in self.table.selectionModel().selectedRows())
        if not selected_rows:
            return
        rows = []
        for row in selected_rows:
            rows.append([self.table.item(row, col).text() for col in range(self.table.columnCount())])
        text = "\n".join(["\t".join(row) for row in rows])
        QApplication.clipboard().setText(text)
        self.statusbar.showMessage("Copied selected row(s) to clipboard.")
        logger.info(f"Copied selected row(s) to clipboard.")

    def copy_current_cell(self):
        current = self.table.currentItem()
        if current is None:
            return
        QApplication.clipboard().setText(current.text())
        self.statusbar.showMessage("Copied current cell to clipboard.")
        logger.info(f"Copied current cell to clipboard.")

    def toggle_column(self, col_index):
        checked = self.column_actions[col_index].isChecked()
        self.table.setColumnHidden(col_index, not checked)

    def save_session(self):
        self.update_comments_dict_from_table()
        default_dir = os.getcwd()
        path, _ = QFileDialog.getSaveFileName(self, "Save Session (JSON)", default_dir, "JSON Files (*.json)")
        if not path:
            return
        try:
            # Prepare data
            session_data = {
                "rows": [
                    {
                        "id": row.id,
                        "testcase": row.testcase,
                        "testopt": row.testopt,
                        "type": row.type,
                        "count": row.count,
                        "message": row.message,
                        "orig_message": row.orig_message,
                        "logtype": row.logtype,
                        "logfilepath": row.logfilepath,
                        "linenumber": row.linenumber
                    }
                    for row in self.filtered_rows
                ],
                "comments": {str(k): v for k, v in self.comments_dict.items()},
                "exclusion_list": list(self.exclusion_list),
                "exclusion_row_keys": [list(k) for k in self.exclusion_row_keys],  # <-- ADD THIS LINE
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            self.statusbar.showMessage(f"Session saved to {path}")
            logger.info(f"Session saved to {path}.")
        except Exception as e:
            QMessageBox.critical(self, "Save Session Error", f"Failed to save session:\n{e}")
            logger.error(f"Save Session Error, Failed to save session:{e}")

    def load_session(self):
        default_dir = os.getcwd()
        path, _ = QFileDialog.getOpenFileName(self, "Load Session (JSON)", default_dir, "JSON Files (*.json)")
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
                session_data = json.load(f)
                # Load rows
                rows = []
                for row in session_data.get("rows", []):
                    # Ensure all fields are present and as strings
                    rows.append(LogRow(
                        str(row.get("id", "")),
                        str(row.get("testcase", "")),
                        str(row.get("testopt", "")),
                        str(row.get("type", "")),
                        int(row.get("count", 0)),
                        str(row.get("message", "")),
                        str(row.get("orig_message", "")),   # <-- add this line
                        str(row.get("logtype", "")),
                        str(row.get("logfilepath", "")),
                        int(row.get("linenumber", 0))
                    ))
                # Load comments
                comments_dict = {}
                for k, v in session_data.get("comments", {}).items():
                    # Convert string key back to tuple
                    try:
                        # The key was saved as str(tuple), so eval is safe here because we control the format
                        key_tuple = eval(k)
                        comments_dict[key_tuple] = v
                    except Exception:
                        continue
                # Load exclusion list
                self.exclusion_list = set(session_data.get("exclusion_list", []))
                self.exclusion_row_keys = set(tuple(k) for k in session_data.get("exclusion_row_keys", []))
    
            self.all_rows = group_rows(rows)
            self.comments_dict = comments_dict
            self.filtered_rows = self.all_rows.copy()
            self.apply_filters()
            self.update_table()
            stats = self.get_message_stats()
            mem = get_memory_usage_mb()
            self.folder_status_label.setText(f"Loaded session file: {os.path.basename(path)}")
            logger.info(f"Loaded session file: {os.path.basename(path)}")
            self.status_label.setText(
                f"Showing {len(self.filtered_rows)} rows | Memory: {mem:.1f} MB | "
                f"<span style='color:#e74c3c;font-weight:bold;'>ERROR: {stats['ERROR']['total']} ({stats['ERROR']['unique']} unique)</span>, "
                f"<span style='color:#8e44ad;font-weight:bold;'>FATAL: {stats['FATAL']['total']} ({stats['FATAL']['unique']} unique)</span>, "
                f"<span style='color:#f1c40f;font-weight:bold;'>WARNING: {stats['WARNING']['total']} ({stats['WARNING']['unique']} unique)</span>"
            )
            self.status_label.setTextFormat(Qt.RichText)
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
                row_key = self.table.item(index.row(), 0).data(Qt.UserRole)
                logrow = next((r for r in self.filtered_rows if self.get_row_key(r) == row_key), None)
                if dlg.result == 'row':
                    self.comments_dict[row_key] = new_text
                elif dlg.result == 'all' and logrow is not None:
                    for r in self.all_rows:
                        if r.orig_message == logrow.orig_message:
                            self.comments_dict[self.get_row_key(r)] = new_text
                self.update_table()
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

    def toggle_dark_mode(self):
        if self.dark_mode_action.isChecked():
            self.setStyleSheet(self.dark_stylesheet)
        else:
            self.setStyleSheet(self.light_stylesheet)

    # --- Find dialog ---
    def show_find_dialog(self):
        dlg = FindDialog(self, self.table, self.columns)
        dlg.exec_()

class LogParseWorker(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)      # all_rows

    def __init__(self, log_files, show_simulate, show_compile, show_scoreboard, patterns, ignore_patterns=None):
        super().__init__()
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
            logger.info(f"Processing file {idx+1}/{len(self.log_files)}: {filepath}")
            id_val, testcase, testopt = extract_log_info(filepath)
            error_counts, fatal_counts, warning_counts = parse_log_file(filepath, self.patterns, self.ignore_patterns)

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

if __name__ == "__main__":

    logfile = 'log/log_triage_process.log'  # or 'log_triage_process.txt'
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
    logger.info("Tool started")

    def log_uncaught_exceptions(exctype, value, tb):
        error_msg = "".join(traceback.format_exception(exctype, value, tb))
        logger.error("Uncaught exception:\n%s", error_msg)
        QMessageBox.critical(None, "Unexpected Error",
            f"An unexpected error occurred:\n\n{value}\n\nSee {logfile} for details.")

    sys.excepthook = log_uncaught_exceptions

    # --- Start the PyQt5 application ---
    app = QApplication(sys.argv)
    win = LogTriageWindow()
    win.show()
    sys.exit(app.exec_())
