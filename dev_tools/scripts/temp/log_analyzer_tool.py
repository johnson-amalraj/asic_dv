import streamlit as st
import pandas as pd
import re
from io import StringIO

st.title("SystemVerilog/UVM Log Analyzer Dashboard")

uploaded_file = st.file_uploader("Upload your simulation log file", type=["log", "txt"])
if uploaded_file:
    # Read the file contents
    log_text = uploaded_file.read().decode("utf-8")
    lines = log_text.splitlines()

    # Patterns
    error_pat = re.compile(r'UVM_ERROR')
    warning_pat = re.compile(r'UVM_WARNING')
    bfm_pat = re.compile(r'BFM_(TXN|TRANSACTION).*', re.IGNORECASE)  # Adjust as needed

    # Extract info
    errors = [l for l in lines if error_pat.search(l)]
    warnings = [l for l in lines if warning_pat.search(l)]
    transactions = [l for l in lines if bfm_pat.search(l)]

    # Display summary
    st.metric("Errors", len(errors))
    st.metric("Warnings", len(warnings))
    st.metric("BFM Transactions", len(transactions))

    # DataFrames for display & export
    df_errors = pd.DataFrame(errors, columns=["Log Line"])
    df_warnings = pd.DataFrame(warnings, columns=["Log Line"])
    df_txn = pd.DataFrame(transactions, columns=["Transaction Line"])

    st.subheader("Errors")
    st.dataframe(df_errors)
    st.download_button("Download Errors CSV", df_errors.to_csv(index=False), "errors.csv")

    st.subheader("Warnings")
    st.dataframe(df_warnings)
    st.download_button("Download Warnings CSV", df_warnings.to_csv(index=False), "warnings.csv")

    st.subheader("BFM Transactions")
    st.dataframe(df_txn)
    st.download_button("Download BFM Transactions CSV", df_txn.to_csv(index=False), "bfm_transactions.csv")

    # (Optional) Bar plot
    st.subheader("Summary Chart")
    chart_data = pd.DataFrame({
        "Type": ["Errors", "Warnings", "BFM Transactions"],
        "Count": [len(errors), len(warnings), len(transactions)]
    })
    st.bar_chart(chart_data.set_index("Type"))

    # (Optional) Show sample lines
    st.subheader("Sample Error Lines")
    st.write(errors[:5])
    st.subheader("Sample BFM Transactions")
    st.write(transactions[:5])

st.info("Tip: Adjust the regex patterns if your log messages use different keywords.")
