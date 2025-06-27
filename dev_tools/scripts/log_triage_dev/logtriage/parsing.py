import re
from collections import Counter, defaultdict
from .utils import clean_message, open_log_file_anytype

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
                    if typ == 'ERROR':
                        errors.append(msg)
                    elif typ == 'WARNING':
                        warnings.append(msg)
                    elif typ == 'FATAL':
                        fatals.append(msg)
                    break

    error_counts = Counter(errors)
    fatal_counts = Counter(fatals)
    warning_counts = Counter(warnings)
    return error_counts, fatal_counts, warning_counts

def extract_log_info(filepath):
    m = re.search(r'/max/([^/]+)', filepath)
    if m:
        name = m.group(1)
    else:
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
    grouped = defaultdict(lambda: [None, None, None, None, 0, None, None, None, None])
    for row in rows:
        key = (row[1], row[2], row[3], row[5], row[6])
        if grouped[key][0] is None:
            grouped[key][0] = row[0]
            grouped[key][1] = row[1]
            grouped[key][2] = row[2]
            grouped[key][3] = row[3]
            grouped[key][4] = 0
            grouped[key][5] = row[5]
            grouped[key][6] = row[6]
            grouped[key][7] = row[7]
            grouped[key][8] = row[8] if len(row) > 8 else ""
        grouped[key][4] += int(row[4])
    return list(grouped.values())