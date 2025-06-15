https://github.com/johnson-amalraj/asic_dv/tree/55d8f4d1c559075ebfcd9b7aae6d78642fd7f2c4/dev_tools/scripts/log_triage_dev

** Open the tool by running below command
  -- LSF   :- bsub -R "rUsage[RAM=10000]" python3 new_ver.py (wrapper script updates required)
  -- Local :- python3 new_ver.py

** TODO

-- Exclusion
    --- Need to re-design the GUI for exclusion
    --- To read the exclusion list and re-apply in the current loaded log path
-- Comments & Feedback
    --- Multi user Comments
    --- If i am exported CSV files, It doesn't have the comemnts column details
 -- DB
    --- Once the particular Log folder opnened and Loaded, If i have updated the comments and added the exclusion list, I have to store the all details with all table information as some .txtformat.
    --- Other users can load the same .txt files in their tool, instead of opening the log file folder to see the already stored information

** Trial ran on below path
-- /home/data/mpu32_simulation/MUSTANG_ST012_A0/simulation_logs/MUSTANG_ST012_A0_HPP_ISS_RTL7_ECO0/RTL_rtl7_eco0_Regression_05_30_2025/max/
