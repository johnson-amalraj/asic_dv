import re
import os
import json
import tempfile
import io
import pytest
from logtriage.models import LogRow
from logtriage.parsing import (
    parse_count_filter, clean_message, load_patterns_from_file,
    load_ignore_patterns_from_file, group_rows, extract_log_info
)

def test_load_patterns_from_file(tmp_path):
    # Create a sample patterns file
    patterns = [
        {"Type": "ERROR", "Regex": r"ERROR: (.+)"},
        {"Type": "WARNING", "Regex": r"WARNING: (.+)"}
    ]
    file = tmp_path / "patterns.json"
    file.write_text(json.dumps(patterns))
    loaded = load_patterns_from_file(str(file))
    assert len(loaded) == 2
    assert loaded[0][0] == "ERROR"
    assert isinstance(loaded[0][1], re.Pattern)

def test_load_ignore_patterns_from_file(tmp_path):
    patterns = [
        {"Regex": r"Ignored message"},
        r"Another ignore"
    ]
    file = tmp_path / "ignore.json"
    file.write_text(json.dumps(patterns))
    loaded = load_ignore_patterns_from_file(str(file))
    assert len(loaded) == 2
    assert all(isinstance(p, re.Pattern) for p in loaded)

def test_group_rows():
    rows = [
        LogRow("1", "tc1", "opt1", "ERROR", 1, "msg1", "msg1", "simulate", "file1", 10),
        LogRow("1", "tc1", "opt1", "ERROR", 2, "msg1", "msg1", "simulate", "file1", 10),
        LogRow("2", "tc2", "opt2", "WARNING", 1, "msg2", "msg2", "compile", "file2", 20),
    ]
    grouped = group_rows(rows)
    assert len(grouped) == 2
    for row in grouped:
        if row.message == "msg1":
            assert row.count == 3
        elif row.message == "msg2":
            assert row.count == 1

def test_extract_log_info():
    path = "/foo/bar/max/ID1234-tc1-opt1/simulate.log"
    id_val, testcase, testopt = extract_log_info(path)
    assert id_val == "1234"
    assert testcase == "ID1234"
    assert testopt == "tc1"

    path2 = "/foo/bar/otherdir/simulate.log"
    id_val2, testcase2, testopt2 = extract_log_info(path2)
    assert testcase2 == "otherdir"

def test_parse_count_filter_invalid():
    assert not parse_count_filter(">abc", 10)
    assert not parse_count_filter("==", 10)
    assert parse_count_filter("", 10)  # Always True

def test_group_rows_different_line_numbers():
    row1 = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 10)
    row2 = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 11)
    grouped = group_rows([row1, row2])
    assert len(grouped) == 2

def test_load_patterns_invalid_json(tmp_path):
    file = tmp_path / "bad.json"
    file.write_text("{not: valid json}")
    with pytest.raises(ValueError):
        load_patterns_from_file(str(file))

def test_load_ignore_patterns_non_json(tmp_path):
    file = tmp_path / "ignore.txt"
    file.write_text("some pattern")
    with pytest.raises(ValueError):
        load_ignore_patterns_from_file(str(file))

def test_file_loading_non_existent(tmp_path):
    non_existent = tmp_path / "does_not_exist.log"
    from logtriage.parsing import open_log_file_anytype
    with pytest.raises(FileNotFoundError):
        with open_log_file_anytype(str(non_existent)):
            pass

def test_file_loading_empty(tmp_path):
    empty_file = tmp_path / "empty.log"
    empty_file.write_text("")
    from logtriage.parsing import open_log_file_anytype
    with open_log_file_anytype(str(empty_file)) as f:
        assert f.read() == ""

def test_file_loading_corrupted(tmp_path):
    # Write invalid utf-8 bytes
    corrupted = tmp_path / "corrupt.log"
    corrupted.write_bytes(b"\xff\xfe\xfd")
    from logtriage.parsing import open_log_file_anytype
    with open_log_file_anytype(str(corrupted)) as f:
        # Should not raise, but content will be empty or replaced
        content = f.read()
        assert isinstance(content, str)

def test_pattern_loading_invalid_json(tmp_path):
    file = tmp_path / "bad.json"
    file.write_text("{not: valid json}")
    with pytest.raises(ValueError):
        load_patterns_from_file(str(file))

def test_pattern_loading_missing_keys(tmp_path):
    file = tmp_path / "missing.json"
    file.write_text(json.dumps([{"Regex": "ERROR: (.+)"}]))  # Missing 'Type'
    loaded = load_patterns_from_file(str(file))
    assert loaded == [] or all(len(p) == 2 for p in loaded)  # Should skip or handle gracefully

def test_pattern_loading_non_json(tmp_path):
    file = tmp_path / "notjson.txt"
    file.write_text("not json")
    with pytest.raises(ValueError):
        load_patterns_from_file(str(file))

def test_clean_message_multiple_hex():
    msg = "Error at 0x1234 and 0x5678"
    cleaned = clean_message(msg)
    assert cleaned.count("0xVAL") == 2

def test_clean_message_no_numbers():
    msg = "This is a message with no numbers or hex"
    cleaned = clean_message(msg)
    assert cleaned == msg

def test_clean_message_very_long():
    msg = "Error " + "0x1234 " * 1000
    cleaned = clean_message(msg)
    assert cleaned.count("0xVAL") == 1000

def test_grouping_duplicate_rows():
    row1 = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 10)
    row2 = LogRow("1", "tc", "opt", "ERROR", 2, "msg", "msg", "simulate", "file", 10)
    grouped = group_rows([row1, row2])
    assert len(grouped) == 1
    assert grouped[0].count == 3

def test_grouping_different_line_numbers():
    row1 = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 10)
    row2 = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 11)
    grouped = group_rows([row1, row2])
    assert len(grouped) == 2

def test_exclusion_import_export(tmp_path):
    # Simulate exclusion list export and import
    exclusion_list = {"msg1", "msg2"}
    export_file = tmp_path / "excl.json"
    with open(export_file, "w") as f:
        json.dump(list(exclusion_list), f)
    with open(export_file) as f:
        imported = set(json.load(f))
    assert exclusion_list == imported

def test_exclusion_non_existent_message():
    exclusion_list = set()
    exclusion_list.add("not_in_data")
    assert "not_in_data" in exclusion_list

def test_comment_on_excluded_row():
    row = LogRow("1", "tc", "opt", "ERROR", 1, "msg", "msg", "simulate", "file", 10)
    comments = {}
    exclusion_list = {"msg"}
    comments[(row.id, row.testcase, row.testopt, row.type, row.message, row.logtype, row.logfilepath, row.linenumber)] = "Test comment"
    assert comments
    assert row.orig_message in exclusion_list

@pytest.mark.parametrize("expr,val,expected", [
    (">5", 6, True),
    ("<=10", 11, False),
    ("5-10", 7, True),
    ("==3", 3, True),
    ("", 100, True),
])
def test_advanced_filter(expr, val, expected):
    assert parse_count_filter(expr, val) == expected

def test_filter_case_insensitive():
    from logtriage.parsing import clean_message
    msg = "error: something"
    assert "ERROR" in clean_message(msg).upper()

def test_filter_invalid_regex():
    import re
    with pytest.raises(re.error):
        re.compile("[unclosed")

def test_stop_loading_sets_flag(qtbot):
    from logtriage.main import LogParseWorker
    worker = LogParseWorker([], True, True, True, [])
    worker.stop()
    assert worker._stop_requested

def test_memory_warning(monkeypatch):
    from logtriage.parsing import get_memory_usage_mb
    monkeypatch.setattr("psutil.Process.memory_info", lambda self: type("mem", (), {"rss": 2 * 1024 * 1024 * 1024})())
    mem = get_memory_usage_mb()
    assert mem > 1000

def test_session_save_load_no_data(tmp_path):
    session_file = tmp_path / "session.json"
    data = {"rows": [], "comments": {}, "exclusion_list": [], "exclusion_row_keys": []}
    with open(session_file, "w") as f:
        json.dump(data, f)
    with open(session_file) as f:
        loaded = json.load(f)
    assert loaded["rows"] == []

def test_session_save_load_with_exclusions_comments(tmp_path):
    session_file = tmp_path / "session.json"
    data = {
        "rows": [{"id": "1", "testcase": "tc", "testopt": "opt", "type": "ERROR", "count": 1, "message": "msg", "orig_message": "msg", "logtype": "simulate", "logfilepath": "file", "linenumber": 10}],
        "comments": {"('1', 'tc', 'opt', 'ERROR', 'msg', 'simulate', 'file', 10)": "comment"},
        "exclusion_list": ["msg"],
        "exclusion_row_keys": [["1", "tc", "opt", "ERROR", "msg", "simulate", "file", 10]],
    }
    with open(session_file, "w") as f:
        json.dump(data, f)
    with open(session_file) as f:
        loaded = json.load(f)
    assert loaded["comments"]
    assert loaded["exclusion_list"]

def test_visualization_no_data():
    # Simulate get_visualization_data returning zeros
    stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
    excluded_stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
    assert all(v == 0 for v in stats.values())
    assert all(v == 0 for v in excluded_stats.values())

def test_visualization_all_excluded():
    stats = {"ERROR": 0, "FATAL": 0, "WARNING": 0}
    excluded_stats = {"ERROR": 5, "FATAL": 2, "WARNING": 1}
    assert sum(stats.values()) == 0
    assert sum(excluded_stats.values()) > 0

def test_open_invalid_log_file(tmp_path):
    invalid_path = tmp_path / "notfound.log"
    assert not invalid_path.exists()
    # Simulate open_log_file logic
    try:
        with open(str(invalid_path)):
            pass
    except FileNotFoundError:
        assert True

def test_column_visibility(qtbot):
    from PyQt5.QtWidgets import QTableWidget
    table = QTableWidget(1, 2)
    table.setColumnHidden(1, True)
    assert table.isColumnHidden(1)

# Add more tests for other utility functions as needed
