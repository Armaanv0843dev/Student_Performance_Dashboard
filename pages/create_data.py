"""
pages/create_data.py

"Create Student Data" page — allows a user to manually enter their academic
marks through a structured form instead of building a CSV/XLSX file by hand.

Subject names and codes are pre-loaded from the known semester mapping.
Totals and Percentage are auto-calculated; the user never types them.

The generated DataFrame is column-compatible with the existing
Upload / Visualization pages of this app.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

# ── Subject mapping (Semester → list of (Subject_Name, Subject_Code)) ─────────
# Sourced directly from sample_data/sample_marks_format.csv
SEMESTER_SUBJECTS: dict[str, list[tuple[str, str]]] = {
    "Semester 1": [
        ("Matrices and Calculus", "NBS4101"),
        ("Engineering Chemistry", "NBS4103"),
        ("Computer Concepts and Programming in C", "NCS4101"),
        ("Basic of Artificial Intelligence", "NCS4102"),
        ("Basic Electrical Engineering", "NEE4101"),
        ("Communicative English", "NHSCC1101"),
        ("Engineering Chemistry Lab", "NBS4153"),
        ("Computer Programming in C Lab", "NCS4151"),
        ("Basic Electrical Engineering Lab", "NEE4151"),
        ("Engineering Graphics Lab", "NME4153"),
        ("General Proficiency", "NGP4101"),
    ],
    "Semester 2": [
        ("Differential Equations and Fourier Analysis", "NBS4201"),
        ("Engineering Physics", "NBS4202"),
        ("Engineering Mechanics", "NME4201"),
        ("Basic Electronics Engineering", "NEC4201"),
        ("Enviroment and Ecological Sustainability", "NBSCC1201"),
        ("Programming Concepts with Python", "NCS4201"),
        ("Engineering Physics Lab", "NBS4252"),
        ("Engineering Mechanics Lab", "NME4251"),
        ("Workshop Practices", "NME4252"),
        ("Python Programming Lab", "NCS4251"),
        ("General Proficiency", "NGP4201"),
    ],
    "Semester 3": [
        ("Complex Analysis and Integral Transforms", "NBS4301"),
        ("Artificial Intelligence in Mechanical Engineering Systems", "NAI4302"),
        ("Discrete Mathematics", "NCS4301"),
        ("Data Structure using 'C'", "NCS4302"),
        ("Digital Logic Design", "NCS4303"),
        ("Industrial Sociology", "NHS4302"),
        ("Indian Constitution", "NVC4301"),
        ("Data Structure Lab", "NCS4352"),
        ("Digital Logic Design Lab", "NCS4353"),
        ("General Proficiency", "NGP4301"),
    ],
    "Semester 4": [
        ("Concepts of Machine Learning With Python", "NAI4401"),
        ("Statistical and Numerical Techniques", "NBS4401"),
        ("Database Management Systems", "NCS4401"),
        ("Operating Systems", "NCS4402"),
        ("Computer Organization & Architecture", "NCS4404"),
        ("Organizational Behavior", "NHS4401"),
        ("Machine Learning Lab", "NAI4451"),
        ("NSS/YOGA", "NCC4451"),
        ("Database Management Systems Lab", "NCS4451"),
        ("General Proficiency", "NGP4401"),
    ],
    "Semester 5": [
        ("Engineering & Managerial Economics", "NHS4501"),
        ("Essence of Indian Knowledge Tradition", "NVC4501"),
        ("Concepts of Data Science with Python", "NAI4501"),
        ("Artificial Neural Network", "NAI4502"),
        ("Computer Networks", "NCS4503"),
        ("Automata Theory and Formal Languages", "NCS4504"),
        ("Data Science with Python Lab", "NAI4551"),
        ("Computer Networks Lab", "NCS4553"),
        ("Artificial Neural Network Lab", "NAI4552"),
        ("Minor Project-I", "NAI4554"),
        ("General Proficiency", "NGP4501"),
    ],
    "Semester 6": [
        ("Industrial Management", "NHS4601"),
        ("Design & Analysis of Algorithms", "NCS4602"),
        ("Compiler Design", "NCS4604"),
        ("Internet of Things", "NPEC43914"),
        ("Computer Vision", "NPEC43922"),
        ("Algorithms Lab", "NCS4652"),
        ("Compiler Design Lab", "NCS4654"),
        ("Seminar", "NAI4651"),
        ("Minor Project-II", "NAI4653"),
        ("General Proficiency", "NGP4601"),
    ],
}

# Subjects whose ESE is "N/A" (internal/project/GP subjects with no ESE)
# Identified from sample_marks_format.csv rows that have N/A for ESE columns.
NO_ESE_CODES = {
    "NGP4101", "NGP4201", "NGP4301", "NGP4401", "NGP4501", "NGP4601",
    "NCC4451", "NAI4554", "NAI4651", "NAI4653",
}

# ── Credit mapping (Subject_Code → Credit) ────────────────────────────────────
# Sourced directly from sample_data/sample_marks_format.csv
SUBJECT_CREDITS: dict[str, int] = {
    # Semester 1
    "NBS4101": 4, "NBS4103": 4, "NCS4101": 3, "NCS4102": 3,
    "NEE4101": 4, "NHSCC1101": 3, "NBS4153": 1, "NCS4151": 1,
    "NEE4151": 1, "NME4153": 1, "NGP4101": 1,
    # Semester 2
    "NBS4201": 4, "NBS4202": 4, "NME4201": 4, "NEC4201": 3,
    "NBSCC1201": 3, "NCS4201": 3, "NBS4252": 1, "NME4251": 1,
    "NME4252": 1, "NCS4251": 1, "NGP4201": 1,
    # Semester 3
    "NBS4301": 4, "NAI4302": 4, "NCS4301": 3, "NCS4302": 4,
    "NCS4303": 3, "NHS4302": 2, "NVC4301": 1, "NCS4352": 1,
    "NCS4353": 1, "NGP4301": 1,
    # Semester 4
    "NAI4401": 3, "NBS4401": 3, "NCS4401": 4, "NCS4402": 4,
    "NCS4404": 4, "NHS4401": 2, "NAI4451": 1, "NCC4451": 1,
    "NCS4451": 1, "NGP4401": 1,
    # Semester 5
    "NHS4501": 3, "NVC4501": 1, "NAI4501": 3, "NAI4502": 3,
    "NCS4503": 3, "NCS4504": 4, "NAI4551": 1, "NCS4553": 1,
    "NAI4552": 1, "NAI4554": 1, "NGP4501": 1,
    # Semester 6
    "NHS4601": 3, "NCS4602": 4, "NCS4604": 4, "NPEC43914": 3,
    "NPEC43922": 3, "NCS4652": 1, "NCS4654": 1, "NAI4651": 1,
    "NAI4653": 1, "NGP4601": 1,
}

FINAL_COLUMNS = [
    "Student_Name", "Semester", "Session",
    "Subject_Name", "Subject_Code",
    "ESE_Obtained", "ESE_Max",
    "CIA_Obtained", "CIA_Max",
    "Total_Obtained", "Total_Max",
    "Credit", "Grade", "SGPA", "Percentage",
]

# ── Helper ────────────────────────────────────────────────────────────────────

def _sem_number(sem_label: str) -> int:
    """Return the numeric part of 'Semester N'."""
    return int(sem_label.split()[-1])


def _safe_pct(total_obtained: float, total_max: float) -> float:
    if total_max and total_max > 0:
        return round(total_obtained / total_max * 100, 2)
    return 0.0


def _grade_from_pct(percentage: float, is_absent: bool = False) -> str:
    """Calculate grade from percentage using the defined grading scale."""
    if is_absent:
        return "AB"
    if percentage >= 90:
        return "O"
    elif percentage >= 75:
        return "A+"
    elif percentage >= 60:
        return "A"
    elif percentage >= 55:
        return "B+"
    elif percentage >= 50:
        return "B"
    elif percentage >= 45:
        return "C"
    elif percentage >= 40:
        return "P"
    else:
        return "F"


def _to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _to_xlsx(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Marks")
    return buf.getvalue()


# ── Page entry point ──────────────────────────────────────────────────────────

def show() -> None:
    # ── Page header ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="page-title">✏️ Create Student Data</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">'
        "Enter your academic marks below — totals, percentage and grade are calculated automatically."
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Section 1 : Student Information ────────────────────────────────────────
    st.subheader("① Student Information")

    col_name, col_sems = st.columns([2, 3])
    with col_name:
        student_name = st.text_input(
            "Student Name *",
            placeholder="e.g. Name Surname",
            key="cd_student_name",
        )
    with col_sems:
        selected_sems = st.multiselect(
            "Select Semester(s) *",
            options=list(SEMESTER_SUBJECTS.keys()),
            default=["Semester 1"],
            key="cd_semesters",
            help="Select one or more semesters. Each semester's data will be included in the final download.",
        )

    # ── Validation of student info ─────────────────────────────────────────────
    info_errors: list[str] = []
    if not student_name.strip():
        info_errors.append("Student Name cannot be empty.")
    if not selected_sems:
        info_errors.append("Please select at least one semester.")

    if info_errors:
        for e in info_errors:
            st.warning(f"⚠️ {e}")

    if not selected_sems:
        st.stop()

    st.divider()

    # ── Section 2 : Per-Semester Marks Entry (Tabs) ────────────────────────────
    st.subheader("② Semester-wise Marks Entry")
    st.caption(
        "Each tab corresponds to a semester you selected. "
        "Fill in Session, SGPA, and marks for each subject. "
        "Unfilled marks default to **0**."
    )

    all_rows: list[dict] = []
    all_errors: list[str] = list(info_errors)

    tabs = st.tabs([f"📚 {sem}" for sem in selected_sems])

    for tab, semester_label in zip(tabs, selected_sems):
        sem_number = _sem_number(semester_label)
        subjects = SEMESTER_SUBJECTS[semester_label]

        with tab:
            # Per-semester Session & SGPA
            ts1, ts2 = st.columns([2, 1])
            with ts1:
                session = st.text_input(
                    f"Session *",
                    placeholder="e.g. 2023-24",
                    key=f"cd_session_{sem_number}",
                )
            with ts2:
                sgpa = st.number_input(
                    "SGPA",
                    min_value=0,
                    max_value=10.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"cd_sgpa_{sem_number}",
                    help="Semester Grade Point Average for this semester.",
                )

            if not session.strip():
                st.warning("⚠️ Session cannot be empty for this semester.")
                all_errors.append(f"Semester {sem_number}: Session is empty.")

            st.caption(
                f"**{len(subjects)} subjects** · Subject Name and Code are pre-filled."
            )

            subject_errors: list[str] = []

            for idx, (sub_name, sub_code) in enumerate(subjects):
                no_ese = sub_code in NO_ESE_CODES
                # Unique key prefix to avoid collision across semesters
                kp = f"s{sem_number}_i{idx}"

                with st.expander(
                    f"📘 {sub_name}  ·  `{sub_code}`",
                    expanded=(idx == 0),
                ):
                    # Read-only subject info row
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.text_input(
                            "Subject Name",
                            value=sub_name,
                            disabled=True,
                            key=f"{kp}_subname",
                        )
                    with rc2:
                        st.text_input(
                            "Subject Code",
                            value=sub_code,
                            disabled=True,
                            key=f"{kp}_subcode",
                        )

                    # ── ESE row ──────────────────────────────────────────────
                    if no_ese:
                        st.info(
                            "ℹ️ This subject has no ESE — fields set to 0 automatically."
                        )
                        ese_obtained: float = 0.0
                        ese_max: float = 0.0
                    else:
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            ese_obtained = st.number_input(
                                "ESE Obtained",
                                min_value=0.0,
                                value=0.0,
                                step=0.5,
                                format="%.1f",
                                key=f"{kp}_ese_obt",
                            )
                        with ec2:
                            ese_max = st.number_input(
                                "ESE Max",
                                min_value=0.0,
                                value=60.0,
                                step=1.0,
                                format="%.1f",
                                key=f"{kp}_ese_max",
                            )
                        if ese_obtained > ese_max:
                            st.error(
                                f"ESE Obtained ({ese_obtained}) cannot exceed ESE Max ({ese_max})."
                            )
                            subject_errors.append(
                                f"Sem {sem_number} · {sub_name}: ESE Obtained > ESE Max."
                            )

                    # ── CIA row ──────────────────────────────────────────────
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        cia_obtained = st.number_input(
                            "CIA Obtained",
                            min_value=0.0,
                            value=0.0,
                            step=0.5,
                            format="%.1f",
                            key=f"{kp}_cia_obt",
                        )
                    with cc2:
                        cia_max = st.number_input(
                            "CIA Max",
                            min_value=0.0,
                            value=100.0 if no_ese else 40.0,
                            step=1.0,
                            format="%.1f",
                            key=f"{kp}_cia_max",
                        )
                    if cia_obtained > cia_max:
                        st.error(
                            f"CIA Obtained ({cia_obtained}) cannot exceed CIA Max ({cia_max})."
                        )
                        subject_errors.append(
                            f"Sem {sem_number} · {sub_name}: CIA Obtained > CIA Max."
                        )

                    # ── Auto-calculated totals ────────────────────────────────
                    total_obtained = ese_obtained + cia_obtained
                    total_max = ese_max + cia_max
                    percentage = _safe_pct(total_obtained, total_max)

                    if total_obtained > total_max:
                        st.error(
                            f"Total Obtained ({total_obtained}) exceeds Total Max ({total_max})."
                        )
                        subject_errors.append(
                            f"Sem {sem_number} · {sub_name}: Total Obtained > Total Max."
                        )

                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        st.metric("Total Obtained", f"{total_obtained:.1f}")
                    with tc2:
                        st.metric("Total Max", f"{total_max:.1f}")
                    with tc3:
                        st.metric("Percentage", f"{percentage:.2f}%")

                    # ── Credit (auto-assigned, optional edit) ─────────────────
                    default_credit = SUBJECT_CREDITS.get(sub_code, 1)
                    edit_credit = st.checkbox(
                        "✏️ Edit Credit",
                        value=False,
                        key=f"{kp}_edit_credit",
                        help="Enable to manually override the pre-assigned credit value.",
                    )
                    if edit_credit:
                        credit = st.number_input(
                            "Credit (Editable)",
                            min_value=0,
                            max_value=10,
                            value=default_credit,
                            step=1,
                            key=f"{kp}_credit",
                        )
                    else:
                        credit = default_credit
                        st.info(f"📌 Credit: **{credit}** (auto-assigned)")

                    # ── Grade (auto-calculated from percentage) ───────────────
                    is_absent = st.checkbox(
                        "🚫 Mark as Absent (AB)",
                        value=False,
                        key=f"{kp}_absent",
                    )
                    grade = _grade_from_pct(percentage, is_absent=is_absent)
                    grade_colors = {
                        "O": "#22c55e", "A+": "#16a34a", "A": "#84cc16",
                        "B+": "#eab308", "B": "#f97316", "C": "#ef4444",
                        "P": "#dc2626", "F": "#991b1b", "AB": "#6b7280",
                    }
                    g_color = grade_colors.get(grade, "#6b7280")
                    st.markdown(
                        f'<div style="display:inline-block;padding:4px 18px;'
                        f'border-radius:20px;background:{g_color};color:#fff;'
                        f'font-weight:700;font-size:1.1rem;margin-top:4px;">'
                        f'Grade: {grade}</div>',
                        unsafe_allow_html=True,
                    )

                # Accumulate row (always, so preview is live)
                all_rows.append(
                    {
                        "Student_Name": student_name.strip(),
                        "Semester": sem_number,
                        "Session": session.strip(),
                        "Subject_Name": sub_name,
                        "Subject_Code": sub_code,
                        "ESE_Obtained": ese_obtained,
                        "ESE_Max": ese_max,
                        "CIA_Obtained": cia_obtained,
                        "CIA_Max": cia_max,
                        "Total_Obtained": total_obtained,
                        "Total_Max": total_max,
                        "Credit": credit,
                        "Grade": grade,
                        "SGPA": sgpa,
                        "Percentage": percentage,
                    }
                )

            all_errors.extend(subject_errors)

    st.divider()

    # ── Section 3 : Data Preview ────────────────────────────────────────────────
    st.subheader("③ Combined Data Preview")
    total_subjects = len(all_rows)
    st.caption(
        f"**{total_subjects} subjects** across **{len(selected_sems)} semester(s)** — "
        "all will be included in the downloaded file."
    )

    df = pd.DataFrame(all_rows, columns=FINAL_COLUMNS)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Section 4 : Download ────────────────────────────────────────────────────
    st.subheader("④ Download")

    blocking_errors = [e for e in all_errors if e]
    if blocking_errors:
        st.error(
            "⛔ Please fix the following issues before downloading:\n\n"
            + "\n".join(f"• {e}" for e in blocking_errors)
        )
    else:
        safe_name = student_name.strip().replace(" ", "_") or "student"
        filename_base = (
            f"{safe_name}_Sem{sem_number}_{session.strip().replace('/', '-')}"
        )

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                label="⬇️ Download CSV",
                data=_to_csv(df),
                file_name=f"{filename_base}.csv",
                mime="text/csv",
                use_container_width=True,
                key="cd_download_csv",
            )
        with dl2:
            st.download_button(
                label="⬇️ Download XLSX",
                data=_to_xlsx(df),
                file_name=f"{filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="cd_download_xlsx",
            )

        st.success(
            "✅ Your data is ready to download. "
            "The generated file is directly compatible with the **Upload Data** page."
        )
