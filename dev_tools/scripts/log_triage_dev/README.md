# Log Triage Dev Tool

This tool is designed to assist in triaging and analyzing simulation log files efficiently. It supports multi-user collaboration, exclusion management, and session persistence.

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Github Path

https://github.com/johnson-amalraj/asic_dv/tree/55d8f4d1c559075ebfcd9b7aae6d78642fd7f2c4/dev_tools/scripts/log_triage_dev

--------------------------------------------------------------------------------------------------------------------------------------------------------

#  How to Run

On LSF: bsub -R "rUsage[RAM=10000]" python3 new_ver.py

On Local : python3 new_ver.py

--------------------------------------------------------------------------------------------------------------------------------------------------------

## Trial ran on below path
/home/data/mpu32_simulation/MUSTANG_ST012_A0/simulation_logs/MUSTANG_ST012_A0_HPP_ISS_RTL7_ECO0/RTL_rtl7_eco0_Regression_05_30_2025/max/

--------------------------------------------------------------------------------------------------------------------------------------------------------

# TODO

## Exclusion
Redesign the GUI for managing exclusions.
Enable reading and reapplying exclusion lists to the currently loaded log path.

## Comments & Feedback
Need to remove the login window.
Instead of the multi user comments, Just i want to store the comments, whoever enters.
Example:
If I opened the log folder/older saved session, I entered the comments, and saved the session.
Others can able to open the session, and add their comments in new line without overriding my comments (they able to see my comments), 
then they can able to save the session. so anyone can able to add comemtns without overriding the existing comments, and save the session with updated comments

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Features
Filtering: Per-column, including numeric range for "Count".
Sorting: Multi-column sorting with Shift+Click.
Exclusion: Add/view/export/import/clear exclusion list.
Summary: Aggregates error/warning/fatal counts per testcase/option.
Export: Filtered data and summary can be exported to CSV.
Find: Regex and plain text search with highlighting.
Persistence: Remembers window size, position, column widths, recent folders, and exclusions.
Error Handling: Logs uncaught exceptions and shows user-friendly error dialogs.

--------------------------------------------------------------------------------------------------------------------------------------------------------
  
# Feature Ideas to Consider

## Visualization:
Add basic charts (e.g., pie chart of error types, timeline of log events).
Heatmap of error frequency over time or modules.

## Tagging System: 
Allow users to tag log entries for categorization.

## Auto-Triage Suggestions: 
Use simple heuristics or ML to suggest likely causes or group similar issues.

## Integration Hooks: 
Allow integration with bug tracking tools (e.g., JIRA) or CI/CD pipelines.

## Dark Mode: 
For better readability during long debugging sessions.

## Command Line Interface (CLI): 
For users who prefer scripting or automation.

## Column Visibility: 
Allow users to hide/show columns (e.g., log file path).

## Advanced Filtering: 
Support AND/OR logic in filters, or allow users to save filter presets.

## Log File Preview: 
On double-click, show a preview of the log message in a dialog, with context lines.

--------------------------------------------------------------------------------------------------------------------------------------------------------
