"""
utils/validation.py

Validates an uploaded marks DataFrame before it is processed.

Supports two schemas:
  • Rich XLSX schema: Subject_Name, ESE_Obtained, ESE_Max, CIA_Obtained,
    CIA_Max, Total_Obtained, Total_Max, Semester, Credit, Grade, SGPA
  • Simple CSV schema: Subject, Marks, Max_Marks, Semester

Checks performed
----------------
1. Required columns are present (flexible for both schemas).
2. Numeric mark columns contain only numeric values.
3. Max marks > 0 for every row.
4. Obtained marks >= 0 for every row.
5. Obtained marks <= Max marks for every row.
6. The DataFrame is not empty after parsing.

Returns a structured result so that the caller (upload page) can display
friendly error messages without duplicating logic.
"""

from __future__ import annotations

import pandas as pd

# Rich XLSX schema — at minimum these must be present.
RICH_REQUIRED = ["Subject_Name", "Total_Obtained", "Total_Max", "Semester"]

# Simple CSV schema — backward compatibility.
SIMPLE_REQUIRED = ["Subject", "Marks", "Max_Marks", "Semester"]

# Optional columns understood by the app.
OPTIONAL_COLUMNS = [
    "Student_Name", "Roll_No", "Branch", "Session", "Subject_Code",
    "ESE_Obtained", "ESE_Max", "CIA_Obtained", "CIA_Max",
    "Credit", "Grade", "SGPA", "Percentage",
    "Exam_Type", "Date",
]


# ── Public API ────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> dict:
    """
    Validate *df* and return a result dictionary.

    Return schema
    -------------
    {
        "valid": bool,
        "errors": list[str],   # blocking problems
        "warnings": list[str], # non-blocking notices
    }
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Empty DataFrame ----------------------------------------------------
    if df.empty:
        errors.append("The uploaded file contains no data rows.")
        return _result(errors, warnings)

    # 2. Detect which schema the file uses and check required columns --------
    schema = _detect_schema(df)
    if schema == "rich":
        obtained_col, max_col = "Total_Obtained", "Total_Max"
        missing = _check_required_columns(df, RICH_REQUIRED)
    elif schema == "simple":
        obtained_col, max_col = "Marks", "Max_Marks"
        missing = _check_required_columns(df, SIMPLE_REQUIRED)
    else:
        # Neither schema matched — report what's closest
        missing_rich = _check_required_columns(df, RICH_REQUIRED)
        missing_simple = _check_required_columns(df, SIMPLE_REQUIRED)
        # Show the schema that is closer (fewer missing cols)
        if len(missing_rich) <= len(missing_simple):
            missing = missing_rich
            obtained_col, max_col = "Total_Obtained", "Total_Max"
        else:
            missing = missing_simple
            obtained_col, max_col = "Marks", "Max_Marks"

    if missing:
        errors.append(
            f"Missing required column(s): **{', '.join(missing)}**. "
            "Please ensure your file has the correct columns and re-upload.\n\n"
            "**Rich XLSX format** needs: `Subject_Name, Total_Obtained, Total_Max, Semester`\n\n"
            "**Simple CSV format** needs: `Subject, Marks, Max_Marks, Semester`"
        )
        return _result(errors, warnings)

    # 3. Numeric column checks ----------------------------------------------
    obtained_errors = _check_numeric_column(df, obtained_col)
    max_errors = _check_numeric_column(df, max_col)
    semester_errors = _check_numeric_column(df, "Semester")

    if obtained_errors:
        errors.append(
            f"Column **{obtained_col}** contains non-numeric value(s) at row(s): "
            f"{_fmt_rows(obtained_errors)}."
        )
    if max_errors:
        errors.append(
            f"Column **{max_col}** contains non-numeric value(s) at row(s): "
            f"{_fmt_rows(max_errors)}."
        )
    if semester_errors:
        warnings.append(
            f"Column **Semester** contains non-numeric value(s) at row(s): "
            f"{_fmt_rows(semester_errors)}. These rows will be kept but "
            "semester-wise charts may not render correctly."
        )

    if obtained_errors or max_errors:
        return _result(errors, warnings)

    # Convert for range checks.
    obtained = pd.to_numeric(df[obtained_col], errors="coerce")
    max_marks = pd.to_numeric(df[max_col], errors="coerce")

    # 4. Max marks > 0 ------------------------------------------------------
    bad_max = df.index[max_marks <= 0].tolist()
    if bad_max:
        errors.append(
            f"**{max_col}** must be greater than 0. "
            f"Problem at row(s): {_fmt_rows(bad_max)}."
        )

    # 5. Obtained >= 0 ------------------------------------------------------
    bad_neg = df.index[obtained < 0].tolist()
    if bad_neg:
        errors.append(
            f"**{obtained_col}** cannot be negative. "
            f"Problem at row(s): {_fmt_rows(bad_neg)}."
        )

    # 6. Obtained <= Max ----------------------------------------------------
    bad_exceed = df.index[obtained > max_marks].tolist()
    if bad_exceed:
        details = []
        for i in bad_exceed[:5]:
            details.append(
                f"Row {i + 2}: {obtained_col}={df.at[i, obtained_col]}, "
                f"{max_col}={df.at[i, max_col]}"
            )
        if len(bad_exceed) > 5:
            details.append(f"… and {len(bad_exceed) - 5} more row(s).")
        errors.append(
            f"**{obtained_col}** cannot exceed **{max_col}** for the following row(s):\n"
            + "\n".join(f"  • {d}" for d in details)
        )

    # Optional ESE/CIA checks if present ------------------------------------
    if "ESE_Obtained" in df.columns and "ESE_Max" in df.columns:
        ese_obt = pd.to_numeric(df["ESE_Obtained"], errors="coerce")
        ese_max = pd.to_numeric(df["ESE_Max"], errors="coerce")
        bad_ese = df.index[(ese_obt.notna() & ese_max.notna()) & (ese_obt > ese_max)].tolist()
        if bad_ese:
            warnings.append(
                f"**ESE_Obtained** exceeds **ESE_Max** at row(s): {_fmt_rows(bad_ese)}."
            )

    if "CIA_Obtained" in df.columns and "CIA_Max" in df.columns:
        cia_obt = pd.to_numeric(df["CIA_Obtained"], errors="coerce")
        cia_max = pd.to_numeric(df["CIA_Max"], errors="coerce")
        bad_cia = df.index[(cia_obt.notna() & cia_max.notna()) & (cia_obt > cia_max)].tolist()
        if bad_cia:
            warnings.append(
                f"**CIA_Obtained** exceeds **CIA_Max** at row(s): {_fmt_rows(bad_cia)}."
            )

    return _result(errors, warnings)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _detect_schema(df: pd.DataFrame) -> str:
    """Return 'rich', 'simple', or 'unknown' based on column presence."""
    cols = set(df.columns)
    if {"Subject_Name", "Total_Obtained", "Total_Max"}.issubset(cols):
        return "rich"
    if {"Subject", "Marks", "Max_Marks"}.issubset(cols):
        return "simple"
    # Partial rich match
    if {"Total_Obtained", "Total_Max"}.issubset(cols):
        return "rich"
    return "unknown"


def _check_required_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """Return a list of required columns that are absent from *df*."""
    return [col for col in required if col not in df.columns]


def _check_numeric_column(df: pd.DataFrame, col: str) -> list[int]:
    """
    Return a list of 0-based row indices where *col* cannot be parsed as a
    number.  Empty list means the column is fully numeric.
    """
    if col not in df.columns:
        return []
    converted = pd.to_numeric(df[col], errors="coerce")
    bad = df.index[converted.isna() & df[col].notna()].tolist()
    return bad


def _fmt_rows(indices: list[int]) -> str:
    """Format a list of 0-based indices as 1-based spreadsheet row numbers."""
    display = [str(i + 2) for i in indices[:10]]
    if len(indices) > 10:
        display.append(f"… +{len(indices) - 10} more")
    return ", ".join(display)


def _result(errors: list[str], warnings: list[str]) -> dict:
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
