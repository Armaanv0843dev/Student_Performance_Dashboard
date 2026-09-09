"""
pages/upload.py

Upload Data page.

Responsibilities
----------------
- Explain the required data format with a clear column reference table.
- Provide a sample CSV download.
- Accept CSV / Excel file uploads.
- Validate the uploaded data, showing user-friendly errors.
- On success, store the clean DataFrame in st.session_state["data"].
- Show a summary and data preview.
- Offer a navigation button to the Visualization page.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from utils import data_processing, validation


# ── Sample file path ───────────────────────────────────────────────────────────
_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "sample_data",
    "sample_marks_format.csv",
)


def show() -> None:
    """Render the Upload Data page."""

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown('<h1 class="page-title">Upload Your Data</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">'
        "Upload your academic marks data to generate your performance dashboard."
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Required Data Format ──────────────────────────────────────────────────
    st.subheader("Required Data Format")
    st.markdown(
        "Your file should contain the following columns. "
        "Download the sample file below to see a working example."
    )

    st.markdown(
        """
| Column | Description | Example |
|---|---|---|
| `Student_Name` | Student's full name | NAME |
| `Semester` | Semester number | 3 |
| `Session` | Academic session | 2023-24 |
| `Subject_Name` | Subject name | Data Structures |
| `Subject_Code` | Subject code | CS301 |
| `ESE_Obtained` | End Sem Exam marks obtained | 68 |
| `ESE_Max` | ESE maximum marks | 80 |
| `CIA_Obtained` | Internal assessment marks obtained | 18 |
| `CIA_Max` | CIA maximum marks | 20 |
| `Total_Obtained` | Total marks obtained | 86 |
| `Total_Max` | Total maximum marks | 100 |
| `Credit` | Credit hours | 4 |
| `Grade` | Letter grade | A |
| `SGPA` | Semester GPA | 8.5 |
| `Percentage` | Score percentage | 86.0 |
"""
    )

    # ── Sample CSV download ───────────────────────────────────────────────────
    if os.path.exists(_SAMPLE_PATH):
        with open(_SAMPLE_PATH, "rb") as f:
            sample_bytes = f.read()
        st.download_button(
            label="⬇️ Download Sample CSV",
            data=sample_bytes,
            file_name="sample_marks_format.csv",
            mime="text/csv",
        )

    st.markdown("---")

    # ── File uploader ─────────────────────────────────────────────────────────
    st.subheader("Upload Your Marks File")
    st.markdown("Accepted formats: **CSV (.csv)**, **Excel (.xlsx, .xls)**")

    uploaded_file = st.file_uploader(
        label="Drag and drop your file here, or click to browse",
        type=["csv", "xlsx", "xls"],
        label_visibility="visible",
    )

    if uploaded_file is None:
        st.info("📂 Upload a CSV or Excel file to get started.")
        return

    # ── Parse file ────────────────────────────────────────────────────────────
    with st.spinner("Reading file…"):
        try:
            raw_df = data_processing.read_file(uploaded_file)
        except ValueError as exc:
            st.error(f"❌ {exc}")
            return
        except Exception as exc:
            st.error(
                "❌ Could not read the file. "
                "Please make sure it is a valid CSV or Excel file."
            )
            return

    # ── Empty file guard ──────────────────────────────────────────────────────
    if raw_df.empty:
        st.error("❌ The uploaded file is empty. Please upload a file that contains data.")
        return

    # ── Validate ──────────────────────────────────────────────────────────────
    result = validation.validate(raw_df)

    if result["errors"]:
        st.error("❌ The file could not be accepted. Please fix the following issue(s) and re-upload:")
        for err in result["errors"]:
            st.markdown(f"- {err}")
        return

    # Show non-blocking warnings
    for w in result["warnings"]:
        st.warning(f"⚠️ {w}")

    # ── Process ───────────────────────────────────────────────────────────────
    with st.spinner("Processing data…"):
        clean_df, notices = data_processing.process(raw_df)

    for n in notices:
        st.info(n)

    if clean_df.empty:
        st.error(
            "❌ No valid rows remain after cleaning. "
            "Please check your data and re-upload."
        )
        return

    # ── Detect schema and store in session state ──────────────────────────────
    schema = data_processing.detect_schema(clean_df)
    st.session_state["data"] = clean_df
    st.session_state["schema"] = schema

    # ── Success ───────────────────────────────────────────────────────────────
    st.success("✅ Data uploaded successfully!")

    # ── Summary metrics ───────────────────────────────────────────────────────
    subject_col = "Subject_Name" if "Subject_Name" in clean_df.columns else "Subject"

    col1, col2, col3 = st.columns(3)
    col1.metric("Records", len(clean_df))
    col2.metric(
        "Subjects",
        clean_df[subject_col].nunique() if subject_col in clean_df.columns else "—",
    )
    col3.metric(
        "Semesters",
        clean_df["Semester"].nunique() if "Semester" in clean_df.columns else "—",
    )

    # ── Data preview ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Data Preview")

    # Show the most relevant columns
    preview_cols_priority = [
        "Student_Name", "Semester", "Subject_Name", "Subject_Code",
        "Total_Obtained", "Total_Max", "Percentage", "Grade", "SGPA",
        # Simple schema fallback
        "Subject", "Marks", "Max_Marks",
    ]
    preview_cols = [c for c in preview_cols_priority if c in clean_df.columns]
    if not preview_cols:
        preview_cols = list(clean_df.columns)

    st.dataframe(clean_df[preview_cols], width="stretch", hide_index=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("---")
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("📊 Go to Visualization", width="stretch", type="primary"):
            st.session_state["page"] = "Visualization"
            st.rerun()
