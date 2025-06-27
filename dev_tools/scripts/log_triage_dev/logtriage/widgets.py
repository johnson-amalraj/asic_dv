from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QWidget, QComboBox
)
from PyQt5.QtCore import Qt

class CommentEditDialog(QDialog):
    def __init__(self, parent=None, initial_comment=""):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Comment")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(initial_comment)
        layout.addWidget(QLabel("Comment:"))
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK", self)
        cancel_btn = QPushButton("Cancel", self)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_comment(self):
        return self.text_edit.toPlainText()

class ExclusionListDialog(QDialog):
    def __init__(self, parent=None, exclusion_list=None):
        super().__init__(parent)
        self.setWindowTitle("Exclusion List")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        if exclusion_list:
            self.text_edit.setPlainText("\n".join(exclusion_list))
        layout.addWidget(QLabel("Edit exclusion patterns (one per line):"))
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK", self)
        cancel_btn = QPushButton("Cancel", self)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_exclusion_list(self):
        return [line.strip() for line in self.text_edit.toPlainText().splitlines() if line.strip()]

class FindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.resize(300, 100)
        layout = QVBoxLayout(self)
        self.input = QLineEdit(self)
        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.input)
        btn_layout = QHBoxLayout()
        find_btn = QPushButton("Find", self)
        cancel_btn = QPushButton("Cancel", self)
        find_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(find_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.input.text()

class SummaryDialog(QDialog):
    def __init__(self, parent=None, summary_data=None):
        super().__init__(parent)
        self.setWindowTitle("Summary")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        if summary_data:
            self.table.setColumnCount(len(summary_data[0]))
            self.table.setRowCount(len(summary_data))
            self.table.setHorizontalHeaderLabels(["Type", "Count", "Example"])
            for row_idx, row in enumerate(summary_data):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row_idx, col_idx, item)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        btn = QPushButton("Close", self)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class ChartDialog(QDialog):
    def __init__(self, parent=None, chart_widget=None):
        super().__init__(parent)
        self.setWindowTitle("Chart")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        if chart_widget:
            layout.addWidget(chart_widget)
        btn = QPushButton("Close",self)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)