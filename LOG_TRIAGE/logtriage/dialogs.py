import os
import matplotlib
import matplotlib.style
import numpy as np

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QComboBox, QTextEdit, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

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
            self.logger.error(f"Regex Error, Invalid regex pattern:{e}.")
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
            self.logger.warning(f"Find", "No matches found.")

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
    def __init__(self, summary_rows, parent=None, statusbar=None, logger=None):
        super().__init__(parent)
        self.logger = logger
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
            self.logger.info(f"Row orig_message: {repr(getattr(row, 'orig_message', row.message))}")
            # ------------------------
            # Filter by logtype
            if not self.show_simulate and row.logtype == "simulate":
                continue
            if not self.show_compile and row.logtype == "compile":
                continue
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
                self.logger.info(f"Summary exported to {path}.")
            QMessageBox.information(self, "Export", f"Summary exported to {path}")
        except Exception as e:
            if self.statusbar:
                self.statusbar.showMessage(f"Failed to export summary: {e}")
                self.logger.error(f"Failed to export summary: {e}.")
            QMessageBox.critical(self, "Export Error", f"Failed to export summary:\n{e}")

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
        # if dark_mode_enabled:
        #     self.setStyleSheet("background-color: #232629; color: #F0F0F0;")

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
                self.logger.info(f"Chart exported to {path}.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export chart:\n{e}")
                self.logger.error(f"Export Error", f"Failed to export chart:{e}")

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

class ExclusionListDialog(QDialog):
    def __init__(self, exclusion_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exclusion List")
        self.resize(600, 400)
        layout = QVBoxLayout(self)

        # Add count label
        count_label = QLabel(f"Total excluded messages: {len(exclusion_list)}")
        self.logger.info(f"Total excluded messages: {len(exclusion_list)}.")
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
