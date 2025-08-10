import re, gzip, json, os
from .models import LogRow
from collections import Counter

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

def parse_log_file(filepath, patterns, ignore_patterns=None, logger=None):
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

