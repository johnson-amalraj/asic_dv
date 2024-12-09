Here’s a collection of scripts tailored for the 8 suggested tools. These are starter implementations and can be enhanced as needed.

1. Log Analyzer Tool

import re

def parse_logs(log_file):
    with open(log_file, 'r') as file:
        lines = file.readlines()

    errors = [line for line in lines if "ERROR" in line]
    warnings = [line for line in lines if "WARNING" in line]

    print(f"Total Errors: {len(errors)}")
    print(f"Total Warnings: {len(warnings)}")

    if errors:
        print("\nSample Errors:")
        for error in errors[:5]:
            print(error.strip())

parse_logs('simulation.log')

2. Waveform Navigator

import pyvcd

def analyze_waveform(vcd_file, signal_name):
    with open(vcd_file, 'r') as file:
        parser = pyvcd.VCDParser(file)
        for signal in parser.signals:
            if signal.name == signal_name:
                print(f"Found signal: {signal.name}")
                print(f"Transitions: {len(signal.transitions)}")
                for transition in signal.transitions[:10]:  # Show first 10
                    print(f"Time: {transition.time}, Value: {transition.value}")

analyze_waveform('waveform.vcd', 'clk')

3. Coverage Debug Tool

import json

def analyze_coverage(coverage_file):
    with open(coverage_file, 'r') as file:
        data = json.load(file)

    uncovered_bins = [item for item in data.get("coverage", []) if item['hits'] == 0]
    for bin in uncovered_bins:
        print(f"Uncovered bin: {bin['name']} in scope: {bin['scope']}")

analyze_coverage('coverage.json')

4. Debugging Dashboard for UVM Testbenches

import pandas as pd
import streamlit as st

# Example data structure
data = {'Component': ['env', 'agent1', 'agent2'],
        'Transactions': [100, 80, 50],
        'Phase': ['run', 'run', 'run']}

df = pd.DataFrame(data)

st.title("UVM Debug Dashboard")
st.write("Component Activity Summary")
st.dataframe(df)

5. Assertion Failure Tracker

import re

def track_assertions(log_file):
    with open(log_file, 'r') as file:
        lines = file.readlines()

    for line in lines:
        if "assertion failed" in line.lower():
            print(f"Assertion Failure: {line.strip()}")

track_assertions('simulation.log')

6. Randomization Debugger

def extract_seed(log_file):
    with open(log_file, 'r') as file:
        lines = file.readlines()

    for line in lines:
        if "SEED" in line.upper():
            print(f"Seed Found: {line.strip()}")

extract_seed('simulation.log')

7. Signal State Tracker

import pandas as pd

def track_signal_state(vcd_file, signal_name):
    # Example placeholder - requires actual parsing library for VCD
    data = {'Time': [0, 10, 20, 30], 'Value': ['0', '1', '0', '1']}
    df = pd.DataFrame(data)

    df.to_csv(f'{signal_name}_state.csv', index=False)
    print(f"State changes exported to {signal_name}_state.csv")

track_signal_state('waveform.vcd', 'clk')

8. Test Plan Tracker

import pandas as pd

def track_test_plan(test_plan_file, coverage_file):
    plan = pd.read_excel(test_plan_file)
    coverage = pd.read_csv(coverage_file)

    # Join test plan with coverage data
    merged = plan.merge(coverage, on='TestID', how='left')
    uncovered = merged[merged['Coverage'] < 100]

    print("Uncovered Test Scenarios:")
    print(uncovered)

track_test_plan('test_plan.xlsx', 'coverage_report.csv')

How to Use These Scripts:
	1.	Replace placeholder files (e.g., simulation.log, waveform.vcd) with actual file paths.
	2.	Install required Python libraries:
	•	pip install pyvcd pandas streamlit openpyxl matplotlib plotly
	3.	Run each script separately or integrate them into a larger tool framework.

If you’d like further customization or more features for any specific tool, let me know!
