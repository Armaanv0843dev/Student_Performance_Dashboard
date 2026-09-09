"""
utils/data_processing.py

Responsible for:
  - Reading CSV / Excel files from an uploaded Streamlit file object.
  - Normalising / cleaning column names.
  - Converting numeric columns.
  - Removing exact duplicate rows.
  - Calculating the Percentage column when missing.
  - Returning a clean, analysis-ready DataFrame.

Supports both the simple schema (Subject, Marks, Max_Marks, Semester)
and the rich XLSX schema:
  Student_Name, Roll_No, Branch, Semester, Session,
  Subject_Name, Subject_Code,
  ESE_Obtained, ESE_Max, CIA_Obtained, CIA_Max,
  Total_Obtained, Total_Max, Credit, Grade, SGPA, Percentage.

This module contains NO Streamlit or visualisation code.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

# ── Column name normalisation map ─────────────────────────────────────────────
# Maps common variations → canonical name.
COLUMN_ALIASES: dict[str, str] = {
    # Student info
    "student_name": "Student_Name",
    "studentname": "Student_Name",
    "name": "Student_Name",
    "roll_no": "Roll_No",
    "rollno": "Roll_No",
    "roll": "Roll_No",
    "enrollment": "Roll_No",
    "branch": "Branch",
    "dept": "Branch",
    "department": "Branch",
    "session": "Session",
    "academic_session": "Session",

    # Subject
    "subject_name": "Subject_Name",
    "subjectname": "Subject_Name",
    "subject": "Subject_Name",
    "sub": "Subject_Name",
    "course": "Subject_Name",
    "course_name": "Subject_Name",
    "subject_code": "Subject_Code",
    "subjectcode": "Subject_Code",
    "code": "Subject_Code",

    # ESE (End Semester Exam)
    "ese_obtained": "ESE_Obtained",
    "ese obtained": "ESE_Obtained",
    "ese_marks": "ESE_Obtained",
    "ese": "ESE_Obtained",
    "ese_max": "ESE_Max",
    "ese max": "ESE_Max",
    "ese_maximum": "ESE_Max",

    # CIA (Continuous Internal Assessment)
    "cia_obtained": "CIA_Obtained",
    "cia obtained": "CIA_Obtained",
    "cia_marks": "CIA_Obtained",
    "cia": "CIA_Obtained",
    "cia_max": "CIA_Max",
    "cia max": "CIA_Max",
    "cia_maximum": "CIA_Max",
    "internal": "CIA_Obtained",
    "internal_marks": "CIA_Obtained",

    # Total
    "total_obtained": "Total_Obtained",
    "totalobtained": "Total_Obtained",
    "marks": "Total_Obtained",
    "mark": "Total_Obtained",
    "score": "Total_Obtained",
    "obtained": "Total_Obtained",
    "marks_obtained": "Total_Obtained",
    "obtained_marks": "Total_Obtained",
    "total_marks": "Total_Max",
    "total_max": "Total_Max",
    "totalmax": "Total_Max",
    "max_marks": "Total_Max",
    "max marks": "Total_Max",
    "maxmarks": "Total_Max",
    "maximum_marks": "Total_Max",
    "total": "Total_Max",
    "out_of": "Total_Max",

    # Credit, Grade, SGPA
    "credit": "Credit",
    "credits": "Credit",
    "credit_hours": "Credit",
    "grade": "Grade",
    "letter_grade": "Grade",
    "sgpa": "SGPA",
    "gpa": "SGPA",
    "semester_gpa": "SGPA",

    # Semester
    "semester": "Semester",
    "sem": "Semester",
    "term": "Semester",

    # Legacy simple-schema compatibility
    "exam_type": "Exam_Type",
    "exam type": "Exam_Type",
    "type": "Exam_Type",
    "date": "Date",

    # Percentage
    "percentage": "Percentage",
    "percent": "Percentage",
    "pct": "Percentage",
}

NUMERIC_COLUMNS = [
    "ESE_Obtained", "ESE_Max",
    "CIA_Obtained", "CIA_Max",
    "Total_Obtained", "Total_Max",
    "Credit", "SGPA", "Percentage",
]


# ── Public API ────────────────────────────────────────────────────────────────

def read_file(uploaded_file) -> pd.DataFrame:
    """
    Read a Streamlit UploadedFile object into a raw DataFrame.

    Supports .csv, .xlsx, and .xls formats.
    Raises ValueError for unsupported extensions.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return _read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        return _read_excel(uploaded_file)
    else:
        raise ValueError(
            f"Unsupported file format: '{uploaded_file.name}'. "
            "Please upload a .csv, .xlsx, or .xls file."
        )


def process(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Clean and enrich *df*.

    Steps
    -----
    1. Strip whitespace from column names.
    2. Normalise column names using COLUMN_ALIASES.
    3. Strip whitespace from string columns.
    4. Convert numeric columns.
    5. Remove exact duplicate rows (warns caller).
    6. Drop rows where required numeric columns are still NaN.
    7. Calculate Percentage column if missing.
    8. Ensure Subject column exists (alias from Subject_Name).

    Returns
    -------
    (clean_df, notices)  where *notices* is a list of informational strings
    the caller can display to the user.
    """
    notices: list[str] = []

    df = df.copy()

    # 1. Clean column names -------------------------------------------------
    df.columns = [str(c).strip() for c in df.columns]

    # 2. Normalise column names --------------------------------------------
    df = _normalise_columns(df)

    # 3. Strip string columns -----------------------------------------------
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # 4. Convert numeric columns --------------------------------------------
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Also attempt Semester conversion (best-effort).
    if "Semester" in df.columns:
        sem_numeric = pd.to_numeric(df["Semester"], errors="coerce")
        if sem_numeric.notna().sum() >= df["Semester"].notna().sum() * 0.8:
            df["Semester"] = sem_numeric

    # 5. Remove exact duplicates --------------------------------------------
    original_len = len(df)
    df = df.drop_duplicates()
    removed = original_len - len(df)
    if removed > 0:
        notices.append(
            f"🗑️ **{removed} exact duplicate row(s)** were automatically "
            "removed from your data."
        )

    # 6. Drop rows where required numerics are NaN -------------------------
    # For rich schema: Total_Obtained / Total_Max are required.
    # For simple schema: fall back to legacy column names.
    if "Total_Obtained" in df.columns and "Total_Max" in df.columns:
        required_numerics = ["Total_Obtained", "Total_Max"]
    else:
        required_numerics = [c for c in ["Marks", "Max_Marks"] if c in df.columns]

    before = len(df)
    df = df.dropna(subset=required_numerics)
    dropped = before - len(df)
    if dropped > 0:
        notices.append(
            f"⚠️ **{dropped} row(s)** with unparseable marks values "
            "were excluded from analysis."
        )

    df = df.reset_index(drop=True)

    # 7. Calculate Percentage -----------------------------------------------
    if "Percentage" not in df.columns or df["Percentage"].isna().all():
        if "Total_Obtained" in df.columns and "Total_Max" in df.columns:
            df["Percentage"] = (
                df["Total_Obtained"] / df["Total_Max"] * 100
            ).round(2)
        elif "Marks" in df.columns and "Max_Marks" in df.columns:
            df["Percentage"] = (
                df["Marks"] / df["Max_Marks"] * 100
            ).round(2)
    else:
        df["Percentage"] = pd.to_numeric(df["Percentage"], errors="coerce").round(2)

    # 8. Create a unified "Subject" column for backward-compat charts -------
    if "Subject_Name" in df.columns and "Subject" not in df.columns:
        df["Subject"] = df["Subject_Name"]

    # 9. Create unified Marks / Max_Marks aliases for legacy chart helpers --
    if "Total_Obtained" in df.columns and "Marks" not in df.columns:
        df["Marks"] = df["Total_Obtained"]
    if "Total_Max" in df.columns and "Max_Marks" not in df.columns:
        df["Max_Marks"] = df["Total_Max"]

    return df, notices


def detect_schema(df: pd.DataFrame) -> str:
    """
    Return 'rich' if the DataFrame uses the XLSX schema,
    or 'simple' if it uses the legacy Subject/Marks/Max_Marks schema.
    """
    rich_cols = {"ESE_Obtained", "ESE_Max", "CIA_Obtained", "CIA_Max",
                 "Total_Obtained", "Total_Max"}
    if rich_cols.intersection(df.columns):
        return "rich"
    return "simple"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_csv(uploaded_file) -> pd.DataFrame:
    """Read a CSV uploaded file, trying common encodings."""
    content = uploaded_file.read()
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "Could not decode the CSV file. "
        "Please save it as UTF-8 and re-upload."
    )


def _read_excel(uploaded_file) -> pd.DataFrame:
    """Read an Excel uploaded file (uses openpyxl for .xlsx)."""
    content = uploaded_file.read()
    return pd.read_excel(io.BytesIO(content))


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename DataFrame columns using COLUMN_ALIASES.

    Strategy
    --------
    For each column, convert it to lowercase + replace spaces with underscores,
    then look it up in the alias map.  If found, rename to the canonical name.
    Unknown columns are left untouched.
    """
    rename_map: dict[str, str] = {}
    used_canonical: set[str] = set()

    for col in df.columns:
        key = col.lower().replace(" ", "_").strip("_")
        canonical = COLUMN_ALIASES.get(key) or COLUMN_ALIASES.get(col.lower().strip())
        if canonical and canonical not in used_canonical:
            rename_map[col] = canonical
            used_canonical.add(canonical)

    return df.rename(columns=rename_map)
