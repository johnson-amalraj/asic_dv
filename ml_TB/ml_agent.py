#!/usr/bin/env python3
"""
Minimal ML agent stub: reads coverage.json and writes next_stim.json
Usage: python3 ml_agent.py coverage.json next_stim.json
Output format (single line): op,a,b  (e.g. "0,12,34")
"""
import sys
import json
import random

cov_in = sys.argv[1]
out_file = sys.argv[2]

try:
    with open(cov_in,'r') as f:
        cov = json.load(f)
except Exception:
    cov = {"uncovered_bins": []}

# Very simple policy: if a specific bin mentioned, craft stimulus to hit it.
bins = cov.get('uncovered_bins', [])
if 'add_zero' in bins:
    # try add with a=0
    op = 0; a = 0; b = random.randint(0,255)
elif 'sub_neg' in bins:
    op = 1; a = 10; b = 20
else:
    op = random.randint(0,3)
    a = random.randint(0,255)
    b = random.randint(0,255)

with open(out_file,'w') as f:
    f.write(f"{op},{a},{b}\n")

print("ML agent wrote:", op, a, b)