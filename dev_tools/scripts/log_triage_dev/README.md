# Log Triage Dev Tool

This tool is designed to assist in triaging and analyzing simulation log files efficiently. It supports multi-user collaboration, exclusion management, and session persistence.

# Github Path

https://github.com/johnson-amalraj/asic_dv/tree/55d8f4d1c559075ebfcd9b7aae6d78642fd7f2c4/dev_tools/scripts/log_triage_dev

--------------------------------------------------------------------------------------------------------------------------------------------------------

#  How to Run

## On LSF:
bsub -R "rUsage[RAM=10000]" python3 new_ver.py

## On Local :
python3 new_ver.py

--------------------------------------------------------------------------------------------------------------------------------------------------------

## Trial ran on below path
/home/data/mpu32_simulation/MUSTANG_ST012_A0/simulation_logs/MUSTANG_ST012_A0_HPP_ISS_RTL7_ECO0/RTL_rtl7_eco0_Regression_05_30_2025/max/

--------------------------------------------------------------------------------------------------------------------------------------------------------

# TODO

## Exclusion
Redesign the GUI for managing exclusions.
Enable reading and reapplying exclusion lists to the currently loaded log path.

## Comments & Feedback
Support multi-user comments.
Ensure exported CSV files include the comments column.

## Session Persistence (DB)
When a log folder is opened and updated (comments, exclusions), save all details in a .txt format.
Allow other users to load the .txt file to view previously stored information without reloading the log folder.

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Strengths of the Tool
## Core Functionality:
Parsing and filtering simulation/compile logs
Multi-column sorting and search
Export to CSV
  
## User Experience:
Simple setup and usage instructions
GUI-based interaction
  
## Collaboration Features:
Multi-user support
Commenting and exclusion management
  
## Persistence:
Session saving and reloading via .txt files

--------------------------------------------------------------------------------------------------------------------------------------------------------

# Suggestions for Improvement
## User Interface Enhancements:
Add tooltips or inline help for each menu option.
Include a progress bar or loading indicator when parsing large logs.
  
## Performance Optimization:
Consider lazy loading or chunked reading for very large log files.
Add memory usage stats or warnings if logs are too large.
  
## Error Handling:
Display user-friendly error messages for unsupported formats or missing files.
Log internal errors to a separate debug file for troubleshooting.
  
## Search Improvements:
Support for regex-based search.
Highlight search terms in the results.
  
## Visualization:
Add basic charts (e.g., pie chart of error types, timeline of log events).
Heatmap of error frequency over time or modules.
  
## Feature Ideas to Consider
Tagging System: Allow users to tag log entries for categorization.
Auto-Triage Suggestions: Use simple heuristics or ML to suggest likely causes or group similar issues.
Integration Hooks: Allow integration with bug tracking tools (e.g., JIRA) or CI/CD pipelines.
Dark Mode: For better readability during long debugging sessions.
Command Line Interface (CLI): For users who prefer scripting or automation.
