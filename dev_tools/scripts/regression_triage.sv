import os
import re
import csv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_keywords(log_file_folder, sim_warn_txt_file_path, sim_err_txt_file_path,
                     com_warn_txt_file_path, com_err_txt_file_path,
                     sim_warn_csv_file_path, sim_err_csv_file_path,
                     com_warn_csv_file_path, com_err_csv_file_path):

    # Regular expressions for warnings and errors
    warning_pattern = re.compile(r'UVM_WARNING')
    error_pattern   = re.compile(r'UVM_ERROR|-E-|-F-')

    # Patterns to extract specific information
    patterns = {
        'project'       : re.compile(r'Project:\s*(\S+)'),
        'test_group'    : re.compile(r'TEST GROUP:\s*(\S+)'),
        'step'          : re.compile(r'STEP:\s*(\S+)'),
        'test_name'     : re.compile(r'Test name:\s*(\S+)'),
        'test_option'   : re.compile(r'Test option:\s*(\S+)'),
        'device_option' : re.compile(r'Device option:\s*(\S+)'),
        'clock_scheme'  : re.compile(r'Clock scheme:\s*(\S+)'),
        'data_base'     : re.compile(r'Database:\s*(\S+)'),
        'sql_id'        : re.compile(r'SQL ID:\s*(\d+)'),
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
                            output_line = "\t".join([
                                extracted_values['project'],
                                extracted_values['test_group'],
                                extracted_values['step'],
                                extracted_values['test_name'],
                                extracted_values['test_option'],
                                extracted_values['device_option'],
                                extracted_values['clock_scheme'],
                                extracted_values['data_base'],
                                sql_id,
                                str(unique_count),
                                cleaned_message
                            ])

                            if message_type == "Warning":
                                warnings_list.append(output_line)
                            elif message_type == "Error":
                                errors_list.append(output_line)
            except IOError as e:
                logging.error(f"Error reading file {out_log_file}: {e}")

    # Function to write lists to TXT and CSV
    def write_to_txt_and_csv(txt_file_path, csv_file_path, data, category):
        try:
            # Write to TXT file
            with open(txt_file_path, 'w') as txt_file:
                for line in data:
                    txt_file.write(line + "\n")
            logging.info(f"{category} logs have been written to {txt_file_path}")

            # Write to CSV file
            with open(csv_file_path, 'w') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    'project', 'test_group', 'step', 'test_name', 'test_option',
                    'device_option', 'clock_scheme', 'data_base', 'sql_id',
                    'count', 'debug_msg'
                ])
                for line in data:
                    parts = line.split('\t')
                    if len(parts) == 11:
                        writer.writerow(parts)
                    else:
                        logging.error(f"Line does not contain the expected number of columns: {line}")
            logging.info(f"{category} logs have been written to {csv_file_path}")
        except IOError as e:
            logging.error(f"Error writing to file {txt_file_path} or {csv_file_path}: {e}")

    # Write to the respective TXT and CSV files
    write_to_txt_and_csv(sim_warn_txt_file_path, sim_warn_csv_file_path, sim_warnings, "Simulation Warnings")
    write_to_txt_and_csv(sim_err_txt_file_path, sim_err_csv_file_path, sim_errors, "Simulation Errors")
    write_to_txt_and_csv(com_warn_txt_file_path, com_warn_csv_file_path, com_warnings, "Compilation Warnings")
    write_to_txt_and_csv(com_err_txt_file_path, com_err_csv_file_path, com_errors, "Compilation Errors")

# File Paths
log_file_folder = '/Users/johnsonamalraj/Documents/triage/logs'

sim_warn_txt_file_path = '/Users/johnsonamalraj/Documents/triage/outputs/sim_warnings.txt'
sim_err_txt_file_path  = '/Users/johnsonamalraj/Documents/triage/outputs/sim_errors.txt'
com_warn_txt_file_path = '/Users/johnsonamalraj/Documents/triage/outputs/com_warnings.txt'
com_err_txt_file_path  = '/Users/johnsonamalraj/Documents/triage/outputs/com_errors.txt'

sim_warn_csv_file_path = '/Users/johnsonamalraj/Documents/triage/outputs/sim_warnings.csv'
sim_err_csv_file_path  = '/Users/johnsonamalraj/Documents/triage/outputs/sim_errors.csv'
com_warn_csv_file_path = '/Users/johnsonamalraj/Documents/triage/outputs/com_warnings.csv'
com_err_csv_file_path  = '/Users/johnsonamalraj/Documents/triage/outputs/com_errors.csv'

extract_keywords(
    log_file_folder,
    sim_warn_txt_file_path, sim_err_txt_file_path,
    com_warn_txt_file_path, com_err_txt_file_path,
    sim_warn_csv_file_path, sim_err_csv_file_path,
    com_warn_csv_file_path, com_err_csv_file_path
)
