# python streamlit run .\log_dashboard.py

import os
import re
import csv
import logging
import pandas as pd
import streamlit as st

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_keywords(log_file_folder):
    """
    Extract warnings and errors from log files and return as DataFrames.
    """
    # Regular expressions for warnings and errors
    warning_pattern = re.compile(r'UVM_WARNING')
    error_pattern = re.compile(r'UVM_ERROR|-E-|-F-')

    # Patterns to extract specific information
    patterns = {
        'project': re.compile(r'Project:\s*(\S+)'),
        'test_group': re.compile(r'TEST GROUP:\s*(\S+)'),
        'step': re.compile(r'STEP:\s*(\S+)'),
        'test_name': re.compile(r'Test name:\s*(\S+)'),
        'test_option': re.compile(r'Test option:\s*(\S+)'),
        'device_option': re.compile(r'Device option:\s*(\S+)'),
        'clock_scheme': re.compile(r'Clock scheme:\s*(\S+)'),
        'data_base': re.compile(r'Database:\s*(\S+)'),
        'sql_id': re.compile(r'SQL ID:\s*(\d+)'),
    }

    # Separate output lines for simulation and compilation logs
    sim_warnings = []
    sim_errors = []
    com_warnings = []
    com_errors = []

    for log_file_name in os.listdir(log_file_folder):
        if log_file_name.endswith('.log'):
            out_log_file = os.path.join(log_file_folder, log_file_name)
            logging.info(f"Reading log file: {out_log_file}")

            extracted_values = {key: "NA" for key in patterns}

            # Determine if the log file is for simulation or compilation
            if 'sim' in log_file_name:
                warnings_list = sim_warnings
                errors_list = sim_errors
            elif 'com' in log_file_name:
                warnings_list = com_warnings
                errors_list = com_errors
            else:
                logging.warning(f"Unknown log type for file {log_file_name}. Skipping.")
                continue

            unique_messages = set()

            try:
                with open(out_log_file, 'r') as log_file:
                    for line in log_file:
                        for key, pattern in patterns.items():
                            match = pattern.search(line)
                            if match:
                                extracted_values[key] = match.group(1)

                    log_file.seek(0)

                    for line in log_file:
                        if warning_pattern.search(line):
                            message_type = "Warning"
                        elif error_pattern.search(line):
                            message_type = "Error"
                        else:
                            continue

                        cleaned_message = re.sub(r'@\s*\d+:\s*', '', line.strip())
                        if cleaned_message not in unique_messages:
                            unique_messages.add(cleaned_message)
                            sql_id = extracted_values['sql_id']
                            if sql_id != "NA":
                                try:
                                    int(sql_id)
                                except ValueError:
                                    sql_id = "NA"

                            unique_count = len(unique_messages)
                            output_line = {
                                'project': extracted_values['project'],
                                'test_group': extracted_values['test_group'],
                                'step': extracted_values['step'],
                                'test_name': extracted_values['test_name'],
                                'test_option': extracted_values['test_option'],
                                'device_option': extracted_values['device_option'],
                                'clock_scheme': extracted_values['clock_scheme'],
                                'data_base': extracted_values['data_base'],
                                'sql_id': sql_id,
                                'count': unique_count,
                                'debug_msg': cleaned_message,
                                'type': message_type
                            }

                            if message_type == "Warning":
                                warnings_list.append(output_line)
                            elif message_type == "Error":
                                errors_list.append(output_line)
            except IOError as e:
                logging.error(f"Error reading file {out_log_file}: {e}")

    # Convert lists to DataFrames
    sim_warnings_df = pd.DataFrame(sim_warnings)
    sim_errors_df = pd.DataFrame(sim_errors)
    com_warnings_df = pd.DataFrame(com_warnings)
    com_errors_df = pd.DataFrame(com_errors)

    return sim_warnings_df, sim_errors_df, com_warnings_df, com_errors_df

def main():
    st.title("Regression Triage Dashboard")
    st.write("Analyze and visualize warnings and errors from log files.")

    # File uploader for log folder
    log_folder = st.text_input("Enter the path to the log folder:")
    if log_folder and os.path.exists(log_folder):
        st.info(f"Processing logs from: {log_folder}")

        # Extract data
        sim_warnings_df, sim_errors_df, com_warnings_df, com_errors_df = extract_keywords(log_folder)

        # Display data
        st.subheader("Simulation Warnings")
        if not sim_warnings_df.empty:
            st.dataframe(sim_warnings_df)
        else:
            st.write("No simulation warnings found.")

        st.subheader("Simulation Errors")
        if not sim_errors_df.empty:
            st.dataframe(sim_errors_df)
        else:
            st.write("No simulation errors found.")

        st.subheader("Compilation Warnings")
        if not com_warnings_df.empty:
            st.dataframe(com_warnings_df)
        else:
            st.write("No compilation warnings found.")

        st.subheader("Compilation Errors")
        if not com_errors_df.empty:
            st.dataframe(com_errors_df)
        else:
            st.write("No compilation errors found.")

        # Add visualizations
        st.subheader("Error and Warning Counts")
        summary_data = {
            "Type": ["Simulation Warnings", "Simulation Errors", "Compilation Warnings", "Compilation Errors"],
            "Count": [
                len(sim_warnings_df),
                len(sim_errors_df),
                len(com_warnings_df),
                len(com_errors_df)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        st.bar_chart(summary_df.set_index("Type"))
    else:
        st.warning("Please enter a valid log folder path.")

if __name__ == "__main__":
    main()
