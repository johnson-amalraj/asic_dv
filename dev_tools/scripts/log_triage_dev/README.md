# Log Triage Dev Tool
This tool is designed to assist in triaging and analyzing simulation log files efficiently. It supports multi-user collaboration, exclusion management, and session persistence.

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Github Path
https://github.com/johnson-amalraj/asic_dv/tree/55d8f4d1c559075ebfcd9b7aae6d78642fd7f2c4/dev_tools/scripts/log_triage_dev

--------------------------------------------------------------------------------------------------------------------------------------------------------

#  How to Run
## On LSF: 
bsub -R "rUsage[RAM=10000]" python3 new_ver.py

## On Local:
python3 new_ver.py

--------------------------------------------------------------------------------------------------------------------------------------------------------

## Trial ran on below path
/home/data/mpu32_simulation/MUSTANG_ST012_A0/simulation_logs/MUSTANG_ST012_A0_HPP_ISS_RTL7_ECO0/RTL_rtl7_eco0_Regression_05_30_2025/max/

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Features

## Log Folder Loading: 
Load and parse multiple simulation and compile log files (simulate.log, compile.log, including .gz compressed files) from a selected directory.

## Error/Warning/Fatal Extraction: 
Automatically extracts and summarizes UVM_ERROR, UVM_WARNING, *E, *F, -E-, and -F- messages from log files.

## Message Normalization: 
Cleans and normalizes log messages to group similar issues together, reducing noise from variable data.

## Interactive Table View: 
Displays all extracted log messages in a sortable and filterable table with columns for ID, Test Case, Test Option, Type, Count, Message, Log Type, Log File Path, and Comments.

## Column Filtering: 
Each column has a filter box for quick, case-insensitive filtering. The Count column supports range and comparison filters (e.g., >5, 1-10).

## Multi-Column Sorting: 
Sort by any column, with support for multi-column sorting using Shift+Click on headers.

## Find/Search: 
Powerful search dialog with regex support to highlight and jump to matching rows.

## Exclusion List: 
Exclude specific messages from the view and manage the exclusion list (add, view, import, export, clear).

## Summary Table: 
View a summary of errors, fatals, and warnings (total and unique) per test case and test option. Export summary to CSV.

## Session Management: 
Save and load sessions, including all rows, comments, and exclusion lists, for easy resumption of work.

## Commenting: 
Add and edit multi-line comments for each row, with persistent storage in sessions and exports.

## Export: 
Export filtered data or summary tables to CSV for reporting or further analysis.

## Recent Folders: 
Quick access to recently loaded log folders.

## Dark Mode: 
Optional dark mode for comfortable viewing.

## Memory Usage Monitoring: 
Displays current memory usage and warns if usage is high.

## Keyboard Shortcuts: 
Extensive shortcut support for all major actions (see Help > Shortcut Keys).

## Context Menu: 
Right-click on table rows for quick actions like copy, exclusion, and viewing comments.

## Robust Error Handling: 
Logs uncaught exceptions and displays user-friendly error dialogs.

## Persistent Settings: 
Remembers window size, position, column widths, and user preferences between sessions.

--------------------------------------------------------------------------------------------------------------------------------------------------------
  
# TODO Feature Ideas to Consider

### Once all the features are added, Need to split the code into different files for re-usage
### Need to add the clear features list

## Visualization:
Add basic charts (e.g., pie chart of error types, timeline of log events).
Heatmap of error frequency over time or modules.

## Tagging System: 
Allow users to tag log entries for categorization.

## Auto-Triage Suggestions: 
Use simple heuristics or ML to suggest likely causes or group similar issues.

## Integration Hooks: 
Allow integration with bug tracking tools (e.g., JIRA) or CI/CD pipelines.

## Command Line Interface (CLI): 
For users who prefer scripting or automation.

## Column Visibility: 
Allow users to hide/show columns (e.g., log file path).

## Advanced Filtering: 
Support AND/OR logic in filters, or allow users to save filter presets.

## Log File Preview: 
On double-click, show a preview of the log message in a dialog, with context lines.

--------------------------------------------------------------------------------------------------------------------------------------------------------
