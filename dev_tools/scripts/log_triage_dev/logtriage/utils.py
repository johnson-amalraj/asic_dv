import re
import gzip

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