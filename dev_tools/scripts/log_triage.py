import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import re
from collections import Counter, defaultdict
import os
import csv
import gzip
import subprocess
import pathlib
import json
from datetime import datetime

# --- Loading timeout threshold (seconds) ---
LOADING_TIMEOUT = 5

# --- Tooltip class with follow-mouse ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)
        widget.bind("<Motion>", self.motion)

    def enter(self, event=None):
        self.show_tip(event)

    def leave(self, event=None):
        self.hide_tip()

    def motion(self, event):
        if self.tipwindow:
            x = event.x_root + 20
            y = event.y_root + 10
            self.tipwindow.wm_geometry(f"+{x}+{y}")

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = (event.x_root + 20) if event else self.widget.winfo_rootx() + 30
        y = (event.y_root + 10) if event else self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "9", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# --- Exclusion list ---
exclusion_list = set()

# --- Remember last folder and column widths ---
LASTFOLDER_FILE = os.path.join(pathlib.Path.home(), ".logtriage_lastfolder")
COLWIDTHS_FILE = os.path.join(pathlib.Path.home(), ".logtriage_colwidths")
RECENTFOLDERS_FILE = os.path.join(pathlib.Path.home(), ".logtriage_recentfolders")
MAX_RECENT_FOLDERS = 5
last_loaded_folder = None

def save_last_folder(folder):
    try:
        with open(LASTFOLDER_FILE, "w") as f:
            f.write(folder)
    except Exception:
        pass

def load_last_folder():
    try:
        with open(LASTFOLDER_FILE, "r") as f:
            folder = f.read().strip()
            if folder and os.path.isdir(folder):
                return folder
    except Exception:
        pass
    return None

def save_colwidths(widths):
    try:
        with open(COLWIDTHS_FILE, "w") as f:
            json.dump(widths, f)
    except Exception:
        pass

def load_colwidths():
    try:
        with open(COLWIDTHS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_recent_folders(folder):
    try:
        folders = load_recent_folders()
        if folder in folders:
            folders.remove(folder)
        folders.insert(0, folder)
        folders = [f for f in folders if os.path.isdir(f)]
        folders = folders[:MAX_RECENT_FOLDERS]
        with open(RECENTFOLDERS_FILE, "w") as f:
            json.dump(folders, f)
    except Exception:
        pass

def load_recent_folders():
    try:
        with open(RECENTFOLDERS_FILE, "r") as f:
            folders = json.load(f)
            return [f for f in folders if os.path.isdir(f)]
    except Exception:
        return []

def clear_recent_folders():
    try:
        with open(RECENTFOLDERS_FILE, "w") as f:
            json.dump([], f)
    except Exception:
        pass
    update_recent_files_menu()
    set_status("Recent files list cleared.", "success")

def clean_message(msg):
    msg = re.sub(r'@\s*\d+:?', '', msg)
    msg = re.sub(r'Actual clock period\s*:\s*\d+\.\d+', 'Actual clock period', msg)
    msg = re.sub(r'Actual Fifo Data\s*:\s*[0-9a-fA-Fx]+', 'Actual Fifo Data', msg)
    msg = re.sub(r'Expected Fifo Data\s*:\s*[0-9a-fA-Fx]+', 'Expected Fifo Data', msg)
    msg = re.sub(r'0x[0-9a-fA-F]+', '0xVAL', msg)
    msg = re.sub(r'\b\d+\b', 'N', msg)
    msg = re.sub(r'\s+', ' ', msg).strip()
    return msg

def extract_log_info(filepath):
    log_path_re = re.compile(r'LOG PATH:\s*(.*)')
    try:
        with open_log_file_anytype(filepath) as f:
            for line in f:
                m = log_path_re.search(line)
                if m:
                    path = m.group(1)
                    max_idx = path.find('/max/')
                    if max_idx != -1:
                        after_max = path[max_idx + len('/max/'):]
                        after_max = after_max.strip("/*")
                        parts = after_max.split('-')
                        testcase = parts[0] if len(parts) > 0 else 'N/A'
                        testopt = parts[1] if len(parts) > 1 else 'N/A'
                        id_str = next((p for p in parts if p.startswith('ID')), 'N/A')
                        id_num = re.sub(r'\D', '', id_str)
                        return id_num, testcase, testopt
    except Exception:
        pass
    base = os.path.basename(filepath)
    name, _ = os.path.splitext(base)
    testcase = name
    testopt = ''
    id_str = ''
    id_num = re.sub(r'\D', '', id_str)
    return id_num, testcase, testopt

def open_log_file_anytype(filepath):
    if filepath.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore')
    else:
        return open(filepath, 'r', encoding='utf-8', errors='ignore')

def parse_log_file(filepath):
    error_pattern = re.compile(r'UVM_ERROR')
    warning_pattern = re.compile(r'UVM_WARNING')
    star_e_pattern = re.compile(r'^\*E')
    star_f_pattern = re.compile(r'^\*F')
    dash_e_pattern = re.compile(r'^-E-')
    dash_f_pattern = re.compile(r'^-F-')
    errors, fatals, warnings = [], [], []

    with open_log_file_anytype(filepath) as f:
        for line in f:
            line_stripped = line.strip()
            if error_pattern.search(line):
                msg = re.sub(r'^.*UVM_ERROR\s*:? ?', '', line_stripped)
                msg = clean_message(msg)
                errors.append(msg)
            elif warning_pattern.search(line):
                msg = re.sub(r'^.*UVM_WARNING\s*:? ?', '', line_stripped)
                msg = clean_message(msg)
                warnings.append(msg)
            elif star_e_pattern.match(line_stripped) or dash_e_pattern.match(line_stripped):
                msg = re.sub(r'^(\*E|-E-)\s*', '', line_stripped)
                msg = clean_message(msg)
                errors.append(msg)
            elif star_f_pattern.match(line_stripped) or dash_f_pattern.match(line_stripped):
                msg = re.sub(r'^(\*F|-F-)\s*', '', line_stripped)
                msg = clean_message(msg)
                fatals.append(msg)
    error_counts = Counter(errors)
    fatal_counts = Counter(fatals)
    warning_counts = Counter(warnings)
    return error_counts, fatal_counts, warning_counts

def find_log_files_in_folder(folder, logtype="simulate"):
    log_files = []
    for rootdir, dirs, files in os.walk(folder):
        for fname in files:
            if fname == f"{logtype}.log" or fname == f"{logtype}.log.gz":
                log_files.append(os.path.join(rootdir, fname))
    return log_files

def process_log_files(filepaths, logtype, progress_callback=None):
    grouped = defaultdict(lambda: {"count": 0, "logfiles": set(), "testopts": set()})
    error_counts, fatal_counts, warning_counts = Counter(), Counter(), Counter()
    total = len(filepaths)
    for idx, filepath in enumerate(filepaths):
        id_str, testcase, testopt = extract_log_info(filepath)
        e_counts, f_counts, w_counts = parse_log_file(filepath)
        for msg, count in e_counts.items():
            key = (testcase, "ERROR", msg)
            grouped[key]["count"] += count
            grouped[key]["logfiles"].add(filepath)
            grouped[key]["testopts"].add(testopt)
        for msg, count in f_counts.items():
            key = (testcase, "FATAL", msg)
            grouped[key]["count"] += count
            grouped[key]["logfiles"].add(filepath)
            grouped[key]["testopts"].add(testopt)
        for msg, count in w_counts.items():
            key = (testcase, "WARNING", msg)
            grouped[key]["count"] += count
            grouped[key]["logfiles"].add(filepath)
            grouped[key]["testopts"].add(testopt)
        error_counts += e_counts
        fatal_counts += f_counts
        warning_counts += w_counts
        if progress_callback:
            progress_callback(idx + 1, total)
    rows = []
    for key, val in grouped.items():
        testcase, typ, msg = key
        count = val["count"]
        logfiles = list(val["logfiles"])
        testopts = ", ".join(sorted(val["testopts"]))
        log_file_display = logfiles[0] if logfiles else ""
        rows.append(("", testcase, testopts, typ, count, msg, logtype, log_file_display))
    return rows, error_counts, fatal_counts, warning_counts

def process_all_selected_logs(progress_callback=None):
    global all_rows, error_counts, fatal_counts, warning_counts
    all_rows = []
    error_counts, fatal_counts, warning_counts = Counter(), Counter(), Counter()
    grouped = defaultdict(lambda: {"count": 0, "logfiles": set(), "testopts": set(), "logtypes": set(), "ids": set()})
    total_files = sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())
    processed_files = 0
    def inner_progress_callback(done, total):
        nonlocal processed_files
        processed_files += 1
        if progress_callback:
            progress_callback(processed_files, total_files)
    for logtype in ["simulate", "compile"]:
        if logtype_vars[logtype].get():
            rows, e, f, w = process_log_files(
                log_files_by_type[logtype], logtype,
                progress_callback=progress_callback
            )
            for row in rows:
                id_str, testcase, testopt, typ, count, msg, logtype, log_file_display = row
                key = (testcase, typ, msg)
                grouped[key]["count"] += count
                grouped[key]["logfiles"].add(log_file_display)
                grouped[key]["testopts"].add(testopt)
                grouped[key]["logtypes"].add(logtype)
                id_val, _, _ = extract_log_info(log_file_display)
                if id_val:
                    grouped[key]["ids"].add(id_val)
            error_counts += e
            fatal_counts += f
            warning_counts += w
    for key, val in grouped.items():
        testcase, typ, msg = key
        count = val["count"]
        logfiles = list(val["logfiles"])
        testopts = ", ".join(sorted(val["testopts"]))
        logtypes = ", ".join(sorted(val["logtypes"]))
        ids = ", ".join(sorted(val["ids"]))
        log_file_display = logfiles[0] if logfiles else ""
        all_rows.append((ids, testcase, testopt, typ, count, msg, logtypes, log_file_display))
    filter_table_columnwise()
    set_status(
        f"Found {sum(error_counts.values())} errors ({len(error_counts)} unique), "
        f"{sum(fatal_counts.values())} fatals ({len(fatal_counts)} unique), and "
        f"{sum(warning_counts.values())} warnings ({len(warning_counts)} unique).",
        "info"
    )

# --- Progress bar and loading popup logic ---
def set_loading_status(text, value=0, maximum=100, mode="determinate"):
    loading_status_var.set(text)
    progress_bar["maximum"] = maximum
    if mode == "determinate":
        progress_bar["mode"] = "determinate"
        progress_bar["value"] = value
    else:
        progress_bar["mode"] = "indeterminate"
        if value:
            progress_bar["value"] = value
        else:
            progress_bar["value"] = 0
    progress_bar.update_idletasks()
    loading_status_label.update_idletasks()

loading_popup = None
loading_popup_timer = None

def show_loading_popup():
    global loading_popup
    if loading_popup is not None:
        return
    loading_popup = tk.Toplevel(root)
    loading_popup.title("Loading...")
    loading_popup.geometry("320x80")
    loading_popup.transient(root)
    loading_popup.grab_set()
    loading_popup.resizable(False, False)
    tk.Label(loading_popup, text="Loading is taking longer than expected...", font=("Segoe UI", 12)).pack(pady=18)
    loading_popup.update_idletasks()

def hide_loading_popup():
    global loading_popup
    if loading_popup is not None:
        loading_popup.destroy()
        loading_popup = None

def start_loading_timeout():
    global loading_popup_timer
    stop_loading_timeout()
    loading_popup_timer = root.after(LOADING_TIMEOUT * 1000, show_loading_popup)

def stop_loading_timeout():
    global loading_popup_timer
    if loading_popup_timer is not None:
        root.after_cancel(loading_popup_timer)
        loading_popup_timer = None
    hide_loading_popup()

def finish_loading_status():
    stop_loading_timeout()
    set_loading_status("Loading completed", progress_bar["maximum"], progress_bar["maximum"], mode="determinate")
    progress_bar.update_idletasks()
    loading_status_label.update_idletasks()
    root.after(1500, lambda: set_loading_status("", 0, 100, mode="determinate"))

def get_loaded_logfile_count():
    return sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())

def open_log_folder():
    global last_loaded_folder
    folder = filedialog.askdirectory(title="Select log folder")
    if not folder:
        return
    last_loaded_folder = folder
    save_last_folder(folder)
    save_recent_folders(folder)
    update_recent_files_menu()
    for logtype in ["simulate", "compile"]:
        log_files_by_type[logtype] = find_log_files_in_folder(folder, logtype)
    total_files = sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())
    if total_files > 0:
        set_loading_status("Loading...", 0, total_files, mode="determinate")
    else:
        set_loading_status("Loading...", 0, 100, mode="indeterminate")
        progress_bar.start(10)
    start_loading_timeout()
    def progress_callback(done, total):
        if total > 0:
            set_loading_status(f"Loading... ({done}/{total})", done, total, mode="determinate")
    process_all_selected_logs(progress_callback=progress_callback)
    nfiles = get_loaded_logfile_count()
    file_label.config(text=f"Loaded logs from folder: {folder}  ({nfiles} log files)")
    if progress_bar["mode"] == "indeterminate":
        progress_bar.stop()
    finish_loading_status()

def load_last_loaded_folder():
    global last_loaded_folder
    folder = load_last_folder()
    if not folder:
        messagebox.showinfo("Load Last Loaded Folder", "No last loaded folder found.")
        return
    if not os.path.isdir(folder):
        messagebox.showinfo("Load Last Loaded Folder", f"Last loaded folder not found:\n{folder}")
        return
    last_loaded_folder = folder
    save_recent_folders(folder)
    update_recent_files_menu()
    for logtype in ["simulate", "compile"]:
        log_files_by_type[logtype] = find_log_files_in_folder(folder, logtype)
    total_files = sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())
    if total_files > 0:
        set_loading_status("Loading...", 0, total_files, mode="determinate")
    else:
        set_loading_status("Loading...", 0, 100, mode="indeterminate")
        progress_bar.start(10)
    start_loading_timeout()
    def progress_callback(done, total):
        if total > 0:
            set_loading_status(f"Loading... ({done}/{total})", done, total, mode="determinate")
    process_all_selected_logs(progress_callback=progress_callback)
    nfiles = get_loaded_logfile_count()
    file_label.config(text=f"Loaded logs from folder: {folder}  ({nfiles} log files)")
    if progress_bar["mode"] == "indeterminate":
        progress_bar.stop()
    finish_loading_status()

def reload_logs():
    global last_loaded_folder
    if not last_loaded_folder or not os.path.isdir(last_loaded_folder):
        messagebox.showinfo("Reload Logs", "No folder loaded yet.")
        return
    save_recent_folders(last_loaded_folder)
    update_recent_files_menu()
    for logtype in ["simulate", "compile"]:
        log_files_by_type[logtype] = find_log_files_in_folder(last_loaded_folder, logtype)
    total_files = sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())
    if total_files > 0:
        set_loading_status("Loading...", 0, total_files, mode="determinate")
    else:
        set_loading_status("Loading...", 0, 100, mode="indeterminate")
        progress_bar.start(10)
    start_loading_timeout()
    def progress_callback(done, total):
        if total > 0:
            set_loading_status(f"Loading... ({done}/{total})", done, total, mode="determinate")
    process_all_selected_logs(progress_callback=progress_callback)
    nfiles = get_loaded_logfile_count()
    file_label.config(text=f"Loaded logs from folder: {last_loaded_folder}  ({nfiles} log files)")
    if progress_bar["mode"] == "indeterminate":
        progress_bar.stop()
    finish_loading_status()

def load_recent_folder(folder):
    global last_loaded_folder
    if not os.path.isdir(folder):
        set_status(f"Folder not found: {folder}", "error")
        return
    last_loaded_folder = folder
    save_last_folder(folder)
    save_recent_folders(folder)
    update_recent_files_menu()
    for logtype in ["simulate", "compile"]:
        log_files_by_type[logtype] = find_log_files_in_folder(folder, logtype)
    total_files = sum(len(log_files_by_type[lt]) for lt in ["simulate", "compile"] if logtype_vars[lt].get())
    if total_files > 0:
        set_loading_status("Loading...", 0, total_files, mode="determinate")
    else:
        set_loading_status("Loading...", 0, 100, mode="indeterminate")
        progress_bar.start(10)
    start_loading_timeout()
    def progress_callback(done, total):
        if total > 0:
            set_loading_status(f"Loading... ({done}/{total})", done, total, mode="determinate")
    process_all_selected_logs(progress_callback=progress_callback)
    nfiles = get_loaded_logfile_count()
    file_label.config(text=f"Loaded logs from folder: {folder}  ({nfiles} log files)")
    if progress_bar["mode"] == "indeterminate":
        progress_bar.stop()
    finish_loading_status()

def update_recent_files_menu():
    recent_folders = load_recent_folders()
    recentmenu.delete(0, tk.END)
    if not recent_folders:
        recentmenu.add_command(label="(No recent folders)", state="disabled")
    else:
        for i, folder in enumerate(recent_folders):
            acc = f"Alt+{i+1}"
            recentmenu.add_command(
                label=folder,
                accelerator=acc,
                command=lambda f=folder: load_recent_folder(f)
            )
    if recent_folders:
        recentmenu.add_separator()
    recentmenu.add_command(label="Clear Recent Files", command=clear_recent_folders)

def on_logtype_checkbox():
    process_all_selected_logs()

def update_table(rows):
    for row in tree.get_children():
        tree.delete(row)
    for row in rows:
        tag = row[3]
        display_row = list(row)
        tree.insert("", "end", values=display_row, tags=(tag,))

def parse_count_filter(expr, value):
    try:
        value = int(value)
    except Exception:
        return False
    expr = expr.strip()
    if not expr or expr == "Count":
        return True
    if expr.startswith(">="):
        try:
            return value >= int(expr[2:])
        except:
            return True
    elif expr.startswith("<="):
        try:
            return value <= int(expr[2:])
        except:
            return True
    elif expr.startswith(">"):
        try:
            return value > int(expr[1:])
        except:
            return True
    elif expr.startswith("<"):
        try:
            return value < int(expr[1:])
        except:
            return True
    elif "-" in expr:
        try:
            parts = expr.split("-")
            low = int(parts[0])
            high = int(parts[1])
            return low <= value <= high
        except:
            return True
    elif expr.startswith("=="):
        try:
            return value == int(expr[2:])
        except:
            return True
    else:
        try:
            return value == int(expr)
        except:
            return True

def filter_table_columnwise(*args):
    global all_rows
    filters = [var.get() if var.get() != placeholders[i] else "" for i, var in enumerate(filter_vars)]
    filtered = []
    show_sbd = show_sbd_var.get()

    for row in all_rows:
        if row[5] in exclusion_list:
            continue
        typ = row[3]
        if typ == "ERROR" and not show_sbd and "sbd_compare" in str(row[5]).lower():
            continue

        match = True
        for i, f in enumerate(filters):
            if not f:
                continue
            if i == 4:
                if not parse_count_filter(f, row[i]):
                    match = False
                    break
            else:
                if f.lower() not in str(row[i]).lower():
                    match = False
                    break
        if match:
            filtered.append(row)
    update_table(filtered)

def sort_table(col, reverse):
    rows = [tree.item(child)["values"] for child in tree.get_children()]
    # Columns to sort as integers
    int_cols = ["ID", "Count"]
    col_name = columns[col]
    def safe_int(val):
        try:
            return int(val)
        except Exception:
            return float('-inf') if reverse else float('inf')
    if col_name in int_cols:
        sorted_rows = sorted(rows, key=lambda x: safe_int(x[col]), reverse=reverse)
    else:
        sorted_rows = sorted(rows, key=lambda x: str(x[col]).lower(), reverse=reverse)
    update_table(sorted_rows)
    tree.heading(columns[col], command=lambda c=col: sort_table(c, not reverse))

# Update heading assignment to capture index correctly
for idx, col in enumerate(columns):
    tree.heading(col, text=col, command=lambda c=idx: sort_table(c, False))

tree.tag_configure("ERROR", foreground="red")
tree.tag_configure("FATAL", foreground="magenta")
tree.tag_configure("WARNING", foreground="orange")

tree.bind("<Double-1>", on_tree_double_click)

def update_filter_entry_positions(event=None):
    x = 0
    for i, col in enumerate(columns):
        col_width = tree.column(col, width=None)
        filter_entries[i].place(x=x, y=0, width=col_width, height=22)
        x += col_width
    reset_btn.place(x=x+8, y=0, width=110, height=22)
    filter_frame.config(height=22)

tree.bind('<Configure>', update_filter_entry_positions)
tree.bind('<Map>', update_filter_entry_positions)
root.after(100, update_filter_entry_positions)

# --- Progress bar, status text, and loaded log files label side by side ---
progress_frame = tk.Frame(root)
progress_frame.pack(fill="x", side="bottom", padx=5, pady=(0,0))

loading_status_var = tk.StringVar()
loading_status_label = tk.Label(progress_frame, textvariable=loading_status_var, anchor="w", font=("Segoe UI", 10, "bold"))
loading_status_label.grid(row=0, column=0, sticky="w", padx=(0,5))

progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
progress_bar.grid(row=0, column=1, sticky="ew", padx=(0,5))

file_label = tk.Label(progress_frame, text="No file loaded.", anchor="w", font=("Segoe UI", 10, "bold"))
file_label.grid(row=0, column=2, sticky="ew", padx=(0,5))

progress_frame.columnconfigure(1, weight=2)  # Progress bar expands more
progress_frame.columnconfigure(2, weight=3)  # File label expands most

# --- Status bar with tooltip and color ---
status_bar = tk.Frame(root, relief="sunken", bd=1)
status_bar.pack(side="bottom", fill="x")

status_label_static = tk.Label(status_bar, text="STATUS:", anchor="w", font=("Segoe UI", 10, "bold"))
status_label_static.pack(side="left", padx=(5,2))

status_var = tk.StringVar()
status_label_dynamic = tk.Label(status_bar, textvariable=status_var, anchor="w", font=("Segoe UI", 10))
status_label_dynamic.pack(side="left", fill="x", expand=True)

ToolTip(status_bar, "This is the status bar. It shows information and actions.")

def set_status(msg, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_var.set(f"[{timestamp}] {msg}")
    if level == "info":
        status_bar.config(bg="#f0f0f0")
        status_label_static.config(bg="#f0f0f0", fg="black")
        status_label_dynamic.config(bg="#f0f0f0", fg="black")
    elif level == "warning":
        status_bar.config(bg="#fff59d")
        status_label_static.config(bg="#fff59d", fg="black")
        status_label_dynamic.config(bg="#fff59d", fg="black")
    elif level == "error":
        status_bar.config(bg="#e57373")
        status_label_static.config(bg="#e57373", fg="white")
        status_label_dynamic.config(bg="#e57373", fg="white")
    elif level == "success":
        status_bar.config(bg="#81c784")
        status_label_static.config(bg="#81c784", fg="white")
        status_label_dynamic.config(bg="#81c784", fg="white")
    else:
        status_bar.config(bg="#f0f0f0")
        status_label_static.config(bg="#f0f0f0", fg="black")
        status_label_dynamic.config(bg="#f0f0f0", fg="black")

def select_all_rows():
    tree.selection_set(tree.get_children())

def deselect_all_rows():
    tree.selection_remove(tree.get_children())

all_rows = []
error_counts, fatal_counts, warning_counts = Counter(), Counter(), Counter()
log_files_by_type = {"simulate": [], "compile": []}

# --- Right-click context menu for copying row (no tooltip) ---
def copy_row_to_clipboard(event):
    item = tree.identify_row(event.y)
    if not item:
        return
    values = tree.item(item, "values")
    if values:
        text = "\t".join(str(v) for v in values[:-1])
        root.clipboard_clear()
        root.clipboard_append(text)
        set_status("Row copied to clipboard.", "success")

def show_context_menu(event):
    item = tree.identify_row(event.y)
    if not item:
        return
    tree.selection_set(item)
    context_menu.tk_popup(event.x_root, event.y_root)

context_menu = tk.Menu(tree, tearoff=0)
context_menu.add_command(label="Copy row to clipboard", command=lambda: copy_row_to_clipboard(last_event))
last_event = None
def on_right_click(event):
    global last_event
    last_event = event
    show_context_menu(event)
tree.bind("<Button-3>", on_right_click)

def on_column_resize(event):
    widths = {col: tree.column(col, width=None) for col in columns}
    save_colwidths(widths)
tree.bind("<ButtonRelease-1>", on_column_resize)

# --- Initialize Recent Files menu on startup ---
update_recent_files_menu()

root.mainloop()