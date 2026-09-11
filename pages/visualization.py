"""
pages/visualization.py

Performance Dashboard page.

Sections
--------
1. Sidebar filters  (Semester, Subject)
2. KPI cards        (Overall %, Average Marks, Best Subject, Weakest Subject)
3. Subject-wise bar chart
4. Semester-wise line chart
5. Marks distribution histogram
6. Performance Insights
7. Download processed data
"""

from __future__ import annotations
import plotly.graph_objects as go

import pandas as pd
import plotly.express as px
import streamlit as st


def show() -> None:
    """Render the Performance Dashboard page."""

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown('<h1 class="page-title">Performance Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">'
        "Explore your academic performance through interactive visualizations."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Guard: no data ────────────────────────────────────────────────────────
    if "data" not in st.session_state or st.session_state["data"] is None:
        st.markdown("---")
        st.info(
            "📂 **No data found.**  \n"
            "Please upload your marks file on the **Upload Data** page first."
        )
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("📤 Go to Upload Data", width="stretch"):
                st.session_state["page"] = "Upload"
                st.rerun()
        return

    df: pd.DataFrame = st.session_state["data"].copy()

    # ── Resolve column names ──────────────────────────────────────────────────
    subject_col = "Subject_Name" if "Subject_Name" in df.columns else "Subject"
    obtained_col = "Total_Obtained" if "Total_Obtained" in df.columns else "Marks"
    max_col = "Total_Max" if "Total_Max" in df.columns else "Max_Marks"

    if subject_col not in df.columns:
        st.error("❌ Subject column missing. Please re-upload your data.")
        return
    if "Percentage" not in df.columns:
        st.error("❌ Percentage column missing. Please re-upload your data.")
        return

    # Ensure unified Subject column for charts
    if "Subject" not in df.columns:
        df["Subject"] = df[subject_col]

    # ── Sidebar filters ───────────────────────────────────────────────────────
    df_filtered = _apply_filters(df, subject_col)

    if df_filtered.empty:
        st.warning("⚠️ No data matches the selected filters. Please adjust your selections.")
        return

    st.markdown("---")

    # ── KPI cards ─────────────────────────────────────────────────────────────
    _render_kpis(df_filtered, obtained_col, max_col, subject_col)

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    _render_subject_bar(df_filtered, subject_col, obtained_col, max_col)
    st.markdown("---")

    _render_semester_line(df_filtered, obtained_col, max_col)
    st.markdown("---")

    _render_distribution(df_filtered)
    st.markdown("---")

    # ── B: ESE vs CIA Grouped Bar ──────────────────────────────────────────────
    _render_ese_cia_bar(df_filtered, subject_col)
    st.markdown("---")

    # ── C: Grade Distribution Donut ───────────────────────────────────────────
    _render_grade_donut(df_filtered)
    st.markdown("---")

    # ── D: Credit-Weighted CGPA Estimator ─────────────────────────────────────
    _render_credit_cgpa(df_filtered)
    st.markdown("---")

    # ── E: Combined CIA Analysis (all semesters) ───────────────────────────────
    _render_combined_cia(df, subject_col)
    st.markdown("---")

    # ── Insights ──────────────────────────────────────────────────────────────
    _render_insights(df_filtered, df, subject_col, obtained_col, max_col)

    st.markdown("---")

    # ── Download ──────────────────────────────────────────────────────────────
    _render_download(df_filtered)


# ── Sidebar filters ───────────────────────────────────────────────────────────

def _derive_year(df: pd.DataFrame) -> pd.DataFrame:
    """Derive an academic Year column from Session or Semester."""
    df = df.copy()
    if "Session" in df.columns:
        # Session like '2023-24' → use as Year label directly
        df["_Year"] = df["Session"].astype(str).str.strip()
    elif "Semester" in df.columns:
        # Fallback: pair semesters → Year (1-2→Y1, 3-4→Y2, …)
        sem_num = pd.to_numeric(df["Semester"], errors="coerce")
        df["_Year"] = sem_num.apply(
            lambda s: f"Year {int((s - 1) // 2) + 1}" if pd.notna(s) else "Unknown"
        )
    else:
        df["_Year"] = "Unknown"
    return df


def _apply_filters(df: pd.DataFrame, subject_col: str) -> pd.DataFrame:
    """Render sidebar filters and return the filtered DataFrame."""

    df = _derive_year(df)

    with st.sidebar:
        st.markdown("---")
        st.subheader("Filters")

        # ── Semester filter ───────────────────────────────────────────────────
        semesters = sorted(df["Semester"].dropna().unique().tolist())
        sem_options = ["All"] + [str(s) for s in semesters]
        semester_filter = st.selectbox(
            "🗓️ Semester",
            options=sem_options,
            index=0,
            key="sem_filter",
        )

        # ── Year filter (Session-based) ───────────────────────────────────────
        years = sorted(df["_Year"].dropna().unique().tolist())
        year_options = ["All"] + years
        year_filter = st.selectbox(
            "📅 Academic Year",
            options=year_options,
            index=0,
            key="year_filter",
            help="Filter by academic session / year (e.g. 2023-24).",
        )

        # ── Subject filter ────────────────────────────────────────────────────
        subjects = sorted(df[subject_col].dropna().unique().tolist())
        sub_options = ["All"] + subjects
        subject_filter = st.selectbox(
            "📖 Subject",
            options=sub_options,
            index=0,
            key="sub_filter",
        )

    filtered = df.copy()
    if semester_filter != "All":
        filtered = filtered[filtered["Semester"].astype(str) == semester_filter]
    if year_filter != "All":
        filtered = filtered[filtered["_Year"] == year_filter]
    if subject_filter != "All":
        filtered = filtered[filtered[subject_col] == subject_filter]

    return filtered


# ── KPI cards ─────────────────────────────────────────────────────────────────

def _render_kpis(
    df: pd.DataFrame,
    obtained_col: str,
    max_col: str,
    subject_col: str,
) -> None:
    """Display KPI metric cards (two rows)."""

    # ── Current/Latest SGPA ───────────────────────────────────────────────────
    latest_sgpa: str = "N/A"
    average_sgpa: str = "N/A"
    if "SGPA" in df.columns and "Semester" in df.columns:
        # One SGPA per semester (take first value per semester to avoid duplicates)
        sem_sgpa = (
            df[["Semester", "SGPA"]]
            .dropna(subset=["SGPA"])
            .groupby(df["Semester"].astype(str))["SGPA"]
            .first()
        )
        if not sem_sgpa.empty:
            latest_sgpa = f"{sem_sgpa.loc[sorted(sem_sgpa.index)[-1]]:.2f}"
            average_sgpa = f"{sem_sgpa.mean():.2f}"
    elif "SGPA" in df.columns:
        sgpa_vals = df["SGPA"].dropna()
        if not sgpa_vals.empty:
            latest_sgpa = f"{sgpa_vals.iloc[-1]:.2f}"
            average_sgpa = f"{sgpa_vals.mean():.2f}"

    # ── Number of unique subjects ─────────────────────────────────────────────
    num_subjects = df[subject_col].nunique() if subject_col in df.columns else 0

    # ── Average Grade (mode of Grade column) ─────────────────────────────────
    avg_grade: str = "N/A"
    if "Grade" in df.columns:
        grades = df["Grade"].dropna()
        if not grades.empty:
            mode_vals = grades.mode()
            avg_grade = str(mode_vals.iloc[0]) if not mode_vals.empty else "N/A"

    # Overall Percentage: weighted (not an average of percentages)
    total_obtained = df[obtained_col].sum() if obtained_col in df.columns else 0
    total_max = df[max_col].sum() if max_col in df.columns else 0
    overall_pct = (total_obtained / total_max * 100) if total_max > 0 else 0.0

    # Per-subject weighted percentage
    subject_pct = (
        df.groupby(subject_col)
        .apply(
            lambda g: (
                g[obtained_col].sum() / g[max_col].sum() * 100
                if obtained_col in g.columns and g[max_col].sum() > 0
                else g["Percentage"].mean()
            ),
            include_groups=False,
        )
        .reset_index(name="Pct")
    )

    best_row = subject_pct.loc[subject_pct["Pct"].idxmax()]
    weak_row = subject_pct.loc[subject_pct["Pct"].idxmin()]

    # ── All KPI cards in one aligned row ──────────────────────────────────────
    # Subject-name cols are wider to reduce truncation; full name shown on hover
    def _short(name: str, n: int = 14) -> str:
        return name if len(name) <= n else name[:n].rstrip() + "…"

    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.1, 1.6, 1.6, 1.1, 1.1, 0.9, 0.9])
    c1.metric("📊 Overall %", f"{overall_pct:.1f}%")
    c2.metric(
        "🏆 Best Subject",
        _short(str(best_row[subject_col])),
        f"{best_row['Pct']:.1f}%",
        help=str(best_row[subject_col]),
    )
    c3.metric(
        "📉 Weakest Subject",
        _short(str(weak_row[subject_col])),
        f"{weak_row['Pct']:.1f}%",
        delta_color="inverse",
        help=str(weak_row[subject_col]),
    )
    c4.metric("🎓 Latest SGPA", latest_sgpa)
    c5.metric("📈 Avg SGPA", average_sgpa)
    c6.metric("📚 Subjects", num_subjects)
    c7.metric("⭐ Avg Grade", avg_grade)


# ── Chart 1: Subject-wise bar ─────────────────────────────────────────────────

def _render_subject_bar(
    df: pd.DataFrame,
    subject_col: str,
    obtained_col: str,
    max_col: str,
) -> None:
    """Bar chart: Percentage per subject."""

    st.subheader("Subject-wise Performance")

    sub_df = (
        df.groupby(subject_col, as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "Percentage": (
                        g[obtained_col].sum() / g[max_col].sum() * 100
                        if obtained_col in g.columns and g[max_col].sum() > 0
                        else g["Percentage"].mean()
                    ),
                    "Total_Obtained": g[obtained_col].sum() if obtained_col in g.columns else None,
                    "Total_Max": g[max_col].sum() if max_col in g.columns else None,
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    sub_df["Percentage"] = sub_df["Percentage"].round(2)
    sub_df = sub_df.sort_values("Percentage", ascending=False)

    fig = px.bar(
        sub_df,
        x=subject_col,
        y="Percentage",
        text=sub_df["Percentage"].apply(lambda v: f"{v:.1f}%"),
        color="Percentage",
        color_continuous_scale="RdYlGn",
        range_y=[0, 110],
        labels={subject_col: "Subject", "Percentage": "Percentage (%)"},
        hover_data={"Percentage": ":.1f"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        xaxis_title="Subject",
        yaxis_title="Percentage (%)",
        height=420,
        xaxis_tickangle=-30,
        margin=dict(t=40, b=80),
    )

    st.plotly_chart(fig, width="stretch")


# ── Chart 2: Semester-wise line ───────────────────────────────────────────────

def _render_semester_line(
    df: pd.DataFrame,
    obtained_col: str,
    max_col: str,
) -> None:
    """Line chart: Average percentage per semester."""

    st.subheader("Semester-wise Performance")

    sem_df = (
        df.groupby("Semester", as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "Avg_Percentage": (
                        g[obtained_col].sum() / g[max_col].sum() * 100
                        if obtained_col in g.columns and g[max_col].sum() > 0
                        else g["Percentage"].mean()
                    )
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    sem_df["_sort"] = pd.to_numeric(sem_df["Semester"], errors="coerce")
    sem_df = sem_df.sort_values("_sort").drop(columns="_sort")
    sem_df["Semester"] = sem_df["Semester"].astype(str)
    sem_df["Avg_Percentage"] = sem_df["Avg_Percentage"].round(2)

    if len(sem_df) < 2:
        if len(sem_df) == 1:
            row = sem_df.iloc[0]
            st.info(
                f"Only one semester of data is available (Semester {row['Semester']}). "
                f"Upload data from multiple semesters to see a performance trend."
            )
            st.metric(
                label=f"Semester {row['Semester']} — Average Percentage",
                value=f"{row['Avg_Percentage']:.1f}%",
            )
        else:
            st.info("Not enough semester data to display a trend chart.")
        return

    fig = px.line(
        sem_df,
        x="Semester",
        y="Avg_Percentage",
        markers=True,
        text=sem_df["Avg_Percentage"].apply(lambda v: f"{v:.1f}%"),
        labels={"Avg_Percentage": "Average Percentage (%)", "Semester": "Semester"},
    )
    fig.update_traces(
        textposition="top center",
        line=dict(color="#3B82F6", width=3),
        marker=dict(size=10, color="#3B82F6", line=dict(width=2, color="white")),
    )
    fig.update_layout(
        xaxis_title="Semester",
        yaxis_title="Average Percentage (%)",
        yaxis_range=[0, 110],
        height=380,
        margin=dict(t=40),
    )
    st.plotly_chart(fig, width="stretch")


# ── Chart 3: Marks distribution histogram ────────────────────────────────────

def _render_distribution(df: pd.DataFrame) -> None:
    """Histogram: distribution of percentages across subjects."""

    st.subheader("Marks Distribution")

    if len(df) < 2:
        st.info("Not enough data points to display a distribution chart.")
        return

    fig = px.histogram(
        df,
        x="Percentage",
        nbins=max(5, min(20, len(df))),
        labels={"Percentage": "Percentage (%)"},
        color_discrete_sequence=["#3B82F6"],
    )
    mean_pct = df["Percentage"].mean()
    fig.add_vline(
        x=mean_pct,
        line_dash="dash",
        line_color="#F59E0B",
        annotation_text=f"Mean: {mean_pct:.1f}%",
        annotation_position="top right",
    )
    fig.update_layout(
        xaxis_title="Percentage (%)",
        yaxis_title="Number of Subjects",
        height=360,
        bargap=0.05,
        margin=dict(t=40),
    )
    st.plotly_chart(fig, width="stretch")


# ── Chart B: ESE vs CIA Grouped Bar ─────────────────────────────────────────

def _render_ese_cia_bar(df: pd.DataFrame, subject_col: str) -> None:
    """Grouped bar: ESE % and CIA % side by side per subject."""

    st.subheader("ESE vs CIA Performance")

    ese_col_obt = "ESE_Obtained"
    ese_col_max = "ESE_Max"
    cia_col_obt = "CIA_Obtained"
    cia_col_max = "CIA_Max"

    needed = [ese_col_obt, ese_col_max, cia_col_obt, cia_col_max]
    if not all(c in df.columns for c in needed):
        st.info("ℹ️ ESE / CIA columns not found in the dataset — cannot render this chart.")
        return

    # Filter out no-ESE subjects (ESE_Max == 0)
    ese_df = df[df[ese_col_max] > 0].copy()

    if ese_df.empty:
        st.info("ℹ️ No subjects with ESE data available.")
        return

    grouped = (
        ese_df.groupby(subject_col, as_index=False)
        .agg(
            ESE_Pct=(ese_col_obt, "sum"),
            ESE_Max=(ese_col_max, "sum"),
            CIA_Pct=(cia_col_obt, "sum"),
            CIA_Max=(cia_col_max, "sum"),
        )
    )
    grouped["ESE %"] = (grouped["ESE_Pct"] / grouped["ESE_Max"] * 100).round(1)
    grouped["CIA %"] = (grouped["CIA_Pct"] / grouped["CIA_Max"] * 100).round(1)
    grouped = grouped.sort_values("ESE %", ascending=False)

    # Melt for grouped bar
    melted = grouped[[subject_col, "ESE %", "CIA %"]].melt(
        id_vars=subject_col, var_name="Component", value_name="Percentage"
    )

    fig = px.bar(
        melted,
        x=subject_col,
        y="Percentage",
        color="Component",
        barmode="group",
        text=melted["Percentage"].apply(lambda v: f"{v:.1f}%"),
        color_discrete_map={"ESE %": "#3B82F6", "CIA %": "#F59E0B"},
        labels={subject_col: "Subject", "Percentage": "Percentage (%)"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_tickangle=-30,
        yaxis_range=[0, 115],
        height=430,
        legend_title_text="Component",
        margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "🔵 **ESE** = End-Semester Exam percentage  ·  "
        "🟡 **CIA** = Continuous Internal Assessment percentage"
    )


# ── Chart C: Grade Distribution Donut ────────────────────────────────────────

def _render_grade_donut(df: pd.DataFrame) -> None:
    """Donut chart: count of each grade."""

    st.subheader("Grade Distribution")

    if "Grade" not in df.columns:
        st.info("ℹ️ Grade column not found — cannot render this chart.")
        return

    grade_order = ["O", "A+", "A", "B+", "B", "C", "P", "F", "AB"]
    grade_colors = {
        "O":  "#22c55e",
        "A+": "#16a34a",
        "A":  "#84cc16",
        "B+": "#eab308",
        "B":  "#f97316",
        "C":  "#ef4444",
        "P":  "#dc2626",
        "F":  "#991b1b",
        "AB": "#6b7280",
    }

    grade_counts = (
        df["Grade"]
        .dropna()
        .astype(str)
        .value_counts()
        .reindex(grade_order)
        .dropna()
        .reset_index()
    )
    grade_counts.columns = ["Grade", "Count"]
    grade_counts = grade_counts[grade_counts["Count"] > 0]

    if grade_counts.empty:
        st.info("ℹ️ No grade data available.")
        return

    colors = [grade_colors.get(g, "#94a3b8") for g in grade_counts["Grade"]]

    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        fig = px.pie(
            grade_counts,
            names="Grade",
            values="Count",
            hole=0.55,
            color="Grade",
            color_discrete_map=grade_colors,
            category_orders={"Grade": grade_order},
        )
        fig.update_traces(
            textinfo="label+percent",
            textfont_size=13,
            marker=dict(colors=colors, line=dict(color="#1e293b", width=2)),
        )
        fig.update_layout(
            height=380,
            showlegend=True,
            legend=dict(orientation="v", x=1.02),
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, width="stretch")

    with col_table:
        st.markdown("**Grade Breakdown**")
        total = grade_counts["Count"].sum()
        grade_counts["Share"] = (grade_counts["Count"] / total * 100).round(1).astype(str) + "%"
        st.dataframe(
            grade_counts.rename(columns={"Count": "Subjects", "Share": "Share"}),
            hide_index=True,
            width="stretch",
        )


# ── Chart D: Credit-Weighted CGPA Estimator ───────────────────────────────────

def _render_credit_cgpa(df: pd.DataFrame) -> None:
    """Credit-weighted percentage per semester + running CGPA estimate."""

    st.subheader("Credit-Weighted Performance Estimator")

    if "Credit" not in df.columns or "Semester" not in df.columns:
        st.info("ℹ️ Credit or Semester column not found — cannot render this chart.")
        return

    # Convert Credit to numeric, drop non-numeric / zero
    work = df.copy()
    work["Credit"] = pd.to_numeric(work["Credit"], errors="coerce")
    work["Percentage"] = pd.to_numeric(work["Percentage"], errors="coerce")
    work = work.dropna(subset=["Credit", "Percentage"])
    work = work[work["Credit"] > 0]

    if work.empty:
        st.info("ℹ️ No valid credit data available.")
        return

    # Weighted avg percentage per semester
    def _weighted_pct(g: pd.DataFrame) -> float:
        total_credits = g["Credit"].sum()
        return (g["Percentage"] * g["Credit"]).sum() / total_credits if total_credits > 0 else 0.00

    sem_weighted = (
        work.groupby("Semester")
        .apply(_weighted_pct, include_groups=False)
        .reset_index(name="Weighted_Pct")
    )
    sem_weighted["_sort"] = pd.to_numeric(sem_weighted["Semester"], errors="coerce")
    sem_weighted = sem_weighted.sort_values("_sort").drop(columns="_sort")
    sem_weighted["Semester"] = "Sem " + sem_weighted["Semester"].astype(str)
    sem_weighted["Weighted_Pct"] = sem_weighted["Weighted_Pct"].round(2)

    # Running cumulative credit-weighted avg (≈ CGPA proxy in %)
    total_credits_list: list[float] = []
    running_weighted: list[float] = []
    cum_credits = 0.0
    cum_weighted = 0.0
    for sem_label in sem_weighted["Semester"]:
        sem_orig = sem_label.replace("Sem ", "")
        g = work[work["Semester"].astype(str) == sem_orig]
        tc = g["Credit"].sum()
        wp = (g["Percentage"] * g["Credit"]).sum()
        cum_credits += tc
        cum_weighted += wp
        running_weighted.append((cum_weighted / cum_credits) if cum_credits > 0 else 0.0)
        total_credits_list.append(cum_credits)
    sem_weighted["Running_Avg"] = [round(v, 2) for v in running_weighted]
    sem_weighted["Cumulative_Credits"] = total_credits_list

    # ── KPI row ──────────────────────────────────────────────────────────────
    overall_cwp = sem_weighted["Running_Avg"].iloc[-1] if not sem_weighted.empty else 0.0
    total_creds = sem_weighted["Cumulative_Credits"].iloc[-1] if not sem_weighted.empty else 0
    best_sem = sem_weighted.loc[sem_weighted["Weighted_Pct"].idxmax(), "Semester"]
    best_pct = sem_weighted["Weighted_Pct"].max()

    k1, k2, k3 = st.columns(3)
    k1.metric("🎯 Cumulative Credit-Wtd %", f"{overall_cwp:.2f}%")
    k2.metric("📦 Total Credits Counted", int(total_creds))
    k3.metric("🏅 Best Semester (weighted)", best_sem, f"{best_pct:.1f}%")

    st.markdown("")

    # ── Dual chart: bar (per-sem weighted %) + line (running cumulative) ──────
    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=sem_weighted["Semester"],
            y=sem_weighted["Weighted_Pct"],
            name="Semester Credit-Wtd %",
            marker_color="#3B82F6",
            text=[f"{v:.2f}%" for v in sem_weighted["Weighted_Pct"]],
            textposition="inside",
            textfont=dict(color="white", size=12, family="Arial Black"),
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sem_weighted["Semester"],
            y=sem_weighted["Running_Avg"],
            name="Cumulative Avg %",
            mode="lines+markers+text",
            line=dict(color="#F59E0B", width=3),
            marker=dict(size=10, color="#F59E0B", line=dict(width=2, color="white")),
            text=[f"{v:.1f}%" for v in sem_weighted["Running_Avg"]],
            textposition="top center",
            textfont=dict(color="#F59E0B", size=11),
            yaxis="y",
        )
    )

    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Percentage (%)", range=[0, 120]),
        xaxis_title="Semester",
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "🔵 **Bars** = credit-weighted % for that semester  ·  "
        "🟡 **Line** = cumulative credit-weighted average (CGPA proxy)"
    )


# ── Performance Insights ──────────────────────────────────────────────────────

def _render_insights(
    df_filtered: pd.DataFrame,
    df_full: pd.DataFrame,
    subject_col: str,
    obtained_col: str,
    max_col: str,
) -> None:
    """Generate and display rule-based performance insights."""

    st.subheader("Performance Insights")

    insights: list[str] = []

    # Per-subject weighted percentage
    subject_pct = (
        df_filtered.groupby(subject_col)
        .apply(
            lambda g: (
                g[obtained_col].sum() / g[max_col].sum() * 100
                if obtained_col in g.columns and g[max_col].sum() > 0
                else g["Percentage"].mean()
            ),
            include_groups=False,
        )
    )

    best_sub = subject_pct.idxmax()
    best_val = subject_pct.max()
    weak_sub = subject_pct.idxmin()
    weak_val = subject_pct.min()

    total_obtained = df_filtered[obtained_col].sum() if obtained_col in df_filtered.columns else 0
    total_max = df_filtered[max_col].sum() if max_col in df_filtered.columns else 0
    overall_pct = (total_obtained / total_max * 100) if total_max > 0 else 0.0

    insights.append(f"Your overall percentage is **{overall_pct:.1f}%**.")
    insights.append(f"Your strongest subject is **{best_sub}** with **{best_val:.1f}%**.")
    insights.append(f"Your weakest subject is **{weak_sub}** with **{weak_val:.1f}%**.")

    # Performance level insight
    if overall_pct >= 85:
        insights.append("Excellent performance — keep it up!")
    elif overall_pct >= 70:
        insights.append("Good performance. There is room to improve further.")
    elif overall_pct >= 50:
        insights.append("Average performance. Consider focusing on weaker subjects.")
    else:
        insights.append("Below average performance. Review your study strategy.")

    # Semester improvement insight (uses full data, not filtered)
    _add_semester_improvement_insight(df_full, insights, obtained_col, max_col)

    for insight in insights:
        st.markdown(f"- {insight}")


def _add_semester_improvement_insight(
    df: pd.DataFrame,
    insights: list[str],
    obtained_col: str,
    max_col: str,
) -> None:
    """Append a semester-over-semester trend insight if data allows."""
    try:
        sem_pct = (
            df.groupby("Semester")
            .apply(
                lambda g: (
                    g[obtained_col].sum() / g[max_col].sum() * 100
                    if obtained_col in g.columns and g[max_col].sum() > 0
                    else g["Percentage"].mean()
                ),
                include_groups=False,
            )
        )
        sem_numeric = sem_pct.copy()
        sem_numeric.index = pd.to_numeric(sem_numeric.index, errors="coerce")
        sem_numeric = sem_numeric.dropna().sort_index()

        if len(sem_numeric) < 2:
            return

        prev_sem = int(sem_numeric.index[-2])
        curr_sem = int(sem_numeric.index[-1])
        prev_pct = sem_numeric.iloc[-2]
        curr_pct = sem_numeric.iloc[-1]
        diff = curr_pct - prev_pct

        if diff > 0:
            insights.append(
                f"Your performance improved by **{diff:.1f} percentage points** "
                f"from Semester {prev_sem} ({prev_pct:.1f}%) to Semester {curr_sem} ({curr_pct:.1f}%)."
            )
        elif diff < 0:
            insights.append(
                f"Your performance declined by **{abs(diff):.1f} percentage points** "
                f"from Semester {prev_sem} ({prev_pct:.1f}%) to Semester {curr_sem} ({curr_pct:.1f}%)."
            )
        else:
            insights.append(
                f"Your performance is stable between Semester {prev_sem} and Semester {curr_sem}."
            )
    except Exception:
        pass


# ── Chart E: CIA / ESE / Lab Bar Charts ─────────────────────────────────────

# Semester colour palette (up to 8 sems)
_SEM_COLOURS = [
    "#3B82F6",  # Sem 1 – blue
    "#10B981",  # Sem 2 – emerald
    "#F59E0B",  # Sem 3 – amber
    "#EF4444",  # Sem 4 – red
    "#8B5CF6",  # Sem 5 – violet
    "#EC4899",  # Sem 6 – pink
    "#06B6D4",  # Sem 7 – cyan
    "#F97316",  # Sem 8 – orange
]


def _sem_colour_map(semesters: list) -> dict:
    """Map each semester label to a fixed colour."""
    sems_sorted = sorted(semesters, key=lambda s: (pd.to_numeric(s, errors="coerce"), s))
    return {
        str(s): _SEM_COLOURS[i % len(_SEM_COLOURS)]
        for i, s in enumerate(sems_sorted)
    }


def _horizontal_bar(
    data: pd.DataFrame,
    subject_col: str,
    pct_col: str,
    obt_col: str,
    max_col: str,
    colour_map: dict,
    sem_col: str = "Semester",
) -> "go.Figure":
    """
    Build a horizontal grouped bar chart of *pct_col* per subject,
    with one bar series per semester, colored by *colour_map*.
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    sems = sorted(data[sem_col].unique(), key=lambda s: (pd.to_numeric(s, errors="coerce"), s))

    for sem in sems:
        sub = data[data[sem_col] == sem].copy()
        sub = sub.sort_values(pct_col, ascending=True)
        short = [s if len(s) <= 32 else s[:30] + "…" for s in sub[subject_col]]

        fig.add_trace(
            go.Bar(
                name=f"Sem {sem}",
                x=sub[pct_col],
                y=short,
                orientation="h",
                marker_color=colour_map.get(str(sem), "#94a3b8"),
                text=[f"{v:.1f}%" for v in sub[pct_col]],
                textposition="outside",
                customdata=sub[[subject_col, obt_col, max_col, sem_col]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"Sem %{{customdata[3]}} · "
                    "%{customdata[1]:.0f} / %{customdata[2]:.0f}<br>"
                    "Score: <b>%{x:.1f}%</b><extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="group",
        xaxis=dict(title="Percentage (%)", range=[0, 118]),
        yaxis_title="",
        height=max(380, len(data[subject_col].unique()) * 44),
        legend=dict(
            title="Semester",
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        margin=dict(t=55, b=30, l=10, r=90),
    )
    return fig


def _render_combined_cia(df: pd.DataFrame, subject_col: str) -> None:
    """
    Three bar-chart tabs with inline Year-wise and Semester-wise filters:
      Tab 1 – CIA % per subject
      Tab 2 – ESE % per subject
      Tab 3 – Lab subjects %
    """
    import plotly.graph_objects as go  # noqa: F401 (needed by _horizontal_bar)

    st.subheader("📊 Combined Marks Analysis — CIA · ESE · Lab")

    work = df.copy()
    work["Semester"] = work["Semester"].astype(str)

    for col in ["CIA_Obtained", "CIA_Max", "ESE_Obtained", "ESE_Max",
                "Total_Obtained", "Total_Max"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    # ── Derive Year column (same logic as _derive_year) ─────────────────────
    if "Session" in work.columns:
        work["_Year"] = work["Session"].astype(str).str.strip()
    elif "Semester" in work.columns:
        sem_num = pd.to_numeric(work["Semester"], errors="coerce")
        work["_Year"] = sem_num.apply(
            lambda s: f"Year {int((s - 1) // 2) + 1}" if pd.notna(s) else "Unknown"
        )
    else:
        work["_Year"] = "Unknown"

    # ── Inline filters ────────────────────────────────────────────────────────
    all_years = sorted(work["_Year"].dropna().unique().tolist())
    all_sems  = sorted(work["Semester"].dropna().unique().tolist(),
                       key=lambda s: (pd.to_numeric(s, errors="coerce"), s))

    fc1, fc2 = st.columns(2)
    with fc1:
        selected_year = st.selectbox(
            "📅 Filter by Academic Year",
            options=["All"] + all_years,
            index=0,
            key="cia_year_filter",
            help="Filter all three tabs by academic session / year.",
        )
    with fc2:
        selected_sem = st.selectbox(
            "🗓️ Filter by Semester",
            options=["All"] + all_sems,
            index=0,
            key="cia_sem_filter",
            help="Filter all three tabs to a specific semester.",
        )

    if selected_year != "All":
        work = work[work["_Year"] == selected_year]
    if selected_sem != "All":
        work = work[work["Semester"] == selected_sem]

    if work.empty:
        st.warning("⚠️ No data for the selected Year / Semester combination.")
        return

    # Rebuild colour map after filtering so it only shows relevant sems
    colour_map = _sem_colour_map(work["Semester"].dropna().unique().tolist())

    filter_note = []
    if selected_year != "All":
        filter_note.append(f"Year **{selected_year}**")
    if selected_sem != "All":
        filter_note.append(f"Semester **{selected_sem}**")
    if filter_note:
        st.caption(f"Showing: {' · '.join(filter_note)}")
    else:
        st.caption("Showing **all semesters**, color-coded by semester.")

    tab_cia, tab_ese, tab_lab = st.tabs([
        "📘 CIA — Subject-wise",
        "📗 ESE — Subject-wise",
        "🔬 Lab — Subject-wise",
    ])

    # ── TAB 1 · CIA ───────────────────────────────────────────────────────────
    with tab_cia:
        if "CIA_Obtained" not in work.columns or "CIA_Max" not in work.columns:
            st.info("ℹ️ CIA columns not found in the dataset.")
        else:
            cia_w = work.dropna(subset=["CIA_Obtained", "CIA_Max"])
            cia_w = cia_w[cia_w["CIA_Max"] > 0].copy()

            if cia_w.empty:
                st.info("No valid CIA data available for the selected filters.")
            else:
                cia_agg = (
                    cia_w.groupby([subject_col, "Semester"], as_index=False)
                    .agg(
                        CIA_Obt=("CIA_Obtained", "sum"),
                        CIA_Max_=("CIA_Max", "sum"),
                    )
                )
                cia_agg["CIA_%"] = (cia_agg["CIA_Obt"] / cia_agg["CIA_Max_"] * 100).round(1)

                overall_cia = (
                    cia_w["CIA_Obtained"].sum() / cia_w["CIA_Max"].sum() * 100
                    if cia_w["CIA_Max"].sum() > 0 else 0.0
                )
                best_row = cia_agg.loc[cia_agg["CIA_%"].idxmax()]
                worst_row = cia_agg.loc[cia_agg["CIA_%"].idxmin()]

                k1, k2, k3 = st.columns(3)
                k1.metric("🎯 Overall CIA %", f"{overall_cia:.1f}%")
                k2.metric(
                    "🏆 Best CIA",
                    (best_row[subject_col][:20] + "…") if len(best_row[subject_col]) > 20
                    else best_row[subject_col],
                    f"{best_row['CIA_%']:.1f}% · Sem {best_row['Semester']}",
                )
                k3.metric(
                    "📉 Weakest CIA",
                    (worst_row[subject_col][:20] + "…") if len(worst_row[subject_col]) > 20
                    else worst_row[subject_col],
                    f"{worst_row['CIA_%']:.1f}% · Sem {worst_row['Semester']}",
                    delta_color="inverse",
                )

                st.markdown("")
                fig_cia = _horizontal_bar(
                    cia_agg, subject_col, "CIA_%", "CIA_Obt", "CIA_Max_", colour_map,
                )
                st.plotly_chart(fig_cia, width="stretch")
                st.caption(
                    "Each bar = CIA % for that subject in that semester. "
                    "Grouped & color-coded by semester."
                )

    # ── TAB 2 · ESE ───────────────────────────────────────────────────────────
    with tab_ese:
        if "ESE_Obtained" not in work.columns or "ESE_Max" not in work.columns:
            st.info("ℹ️ ESE columns not found in the dataset.")
        else:
            ese_w = work.dropna(subset=["ESE_Obtained", "ESE_Max"])
            ese_w = ese_w[ese_w["ESE_Max"] > 0].copy()

            if ese_w.empty:
                st.info("No valid ESE data available for the selected filters.")
            else:
                ese_agg = (
                    ese_w.groupby([subject_col, "Semester"], as_index=False)
                    .agg(
                        ESE_Obt=("ESE_Obtained", "sum"),
                        ESE_Max_=("ESE_Max", "sum"),
                    )
                )
                ese_agg["ESE_%"] = (ese_agg["ESE_Obt"] / ese_agg["ESE_Max_"] * 100).round(1)

                overall_ese = (
                    ese_w["ESE_Obtained"].sum() / ese_w["ESE_Max"].sum() * 100
                    if ese_w["ESE_Max"].sum() > 0 else 0.0
                )
                best_row = ese_agg.loc[ese_agg["ESE_%"].idxmax()]
                worst_row = ese_agg.loc[ese_agg["ESE_%"].idxmin()]

                k1, k2, k3 = st.columns(3)
                k1.metric("🎯 Overall ESE %", f"{overall_ese:.1f}%")
                k2.metric(
                    "🏆 Best ESE",
                    (best_row[subject_col][:20] + "…") if len(best_row[subject_col]) > 20
                    else best_row[subject_col],
                    f"{best_row['ESE_%']:.1f}% · Sem {best_row['Semester']}",
                )
                k3.metric(
                    "📉 Weakest ESE",
                    (worst_row[subject_col][:20] + "…") if len(worst_row[subject_col]) > 20
                    else worst_row[subject_col],
                    f"{worst_row['ESE_%']:.1f}% · Sem {worst_row['Semester']}",
                    delta_color="inverse",
                )

                st.markdown("")
                fig_ese = _horizontal_bar(
                    ese_agg, subject_col, "ESE_%", "ESE_Obt", "ESE_Max_", colour_map,
                )
                st.plotly_chart(fig_ese, width="stretch")
                st.caption(
                    "Each bar = ESE % for that subject in that semester. "
                    "Grouped & color-coded by semester."
                )

    # ── TAB 3 · LAB ───────────────────────────────────────────────────────────
    with tab_lab:
        # Detect lab/practical subjects:
        # 1) Subject name contains 'lab' (case-insensitive, whole word)
        # 2) OR ESE_Max == 0 (pure internal / practical)
        # Exclude 'General Proficiency' — kept only in CIA tab
        gp_mask = work[subject_col].str.contains(
            r"general.?proficiency", case=False, na=False, regex=True
        )
        lab_mask = work[subject_col].str.contains(
            r"\blab\b", case=False, na=False, regex=True
        )
        if "ESE_Max" in work.columns:
            lab_mask = lab_mask | (work["ESE_Max"].fillna(0) == 0)

        # Remove GP from lab set
        lab_mask = lab_mask & ~gp_mask

        lab_w = work[lab_mask].copy()

        if lab_w.empty:
            st.info(
                "ℹ️ No lab/practical subjects found for the selected filters. "
                "Detected by 'Lab' in subject name or subjects with no ESE component."
            )
        else:
            obt_c = "Total_Obtained" if "Total_Obtained" in lab_w.columns else "CIA_Obtained"
            max_c = "Total_Max" if "Total_Max" in lab_w.columns else "CIA_Max"

            lab_w2 = lab_w.dropna(subset=[obt_c, max_c])
            lab_w2 = lab_w2[lab_w2[max_c] > 0].copy()

            if lab_w2.empty:
                st.info("No valid lab marks data for the selected filters.")
            else:
                lab_agg = (
                    lab_w2.groupby([subject_col, "Semester"], as_index=False)
                    .agg(
                        Lab_Obt=(obt_c, "sum"),
                        Lab_Max_=(max_c, "sum"),
                    )
                )
                lab_agg["Lab_%"] = (lab_agg["Lab_Obt"] / lab_agg["Lab_Max_"] * 100).round(1)

                overall_lab = (
                    lab_w2[obt_c].sum() / lab_w2[max_c].sum() * 100
                    if lab_w2[max_c].sum() > 0 else 0.0
                )
                best_row = lab_agg.loc[lab_agg["Lab_%"].idxmax()]
                worst_row = lab_agg.loc[lab_agg["Lab_%"].idxmin()]

                k1, k2, k3 = st.columns(3)
                k1.metric("🔬 Overall Lab %", f"{overall_lab:.1f}%")
                k2.metric(
                    "🏆 Best Lab",
                    (best_row[subject_col][:22] + "…") if len(best_row[subject_col]) > 22
                    else best_row[subject_col],
                    f"{best_row['Lab_%']:.1f}% · Sem {best_row['Semester']}",
                )
                k3.metric(
                    "📉 Weakest Lab",
                    (worst_row[subject_col][:22] + "…") if len(worst_row[subject_col]) > 22
                    else worst_row[subject_col],
                    f"{worst_row['Lab_%']:.1f}% · Sem {worst_row['Semester']}",
                    delta_color="inverse",
                )

                st.markdown("")
                fig_lab = _horizontal_bar(
                    lab_agg, subject_col, "Lab_%", "Lab_Obt", "Lab_Max_", colour_map,
                )
                st.plotly_chart(fig_lab, width="stretch")
                st.caption(
                    "Lab subjects = 'Lab' in subject name OR no ESE component. "
                    "Score = Total marks % for that practical."
                )


# ── Download ──────────────────────────────────────────────────────────────────

def _render_download(df: pd.DataFrame) -> None:
    """Render a download button for the processed CSV."""

    st.subheader("Download Processed Data")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_bytes,
        file_name="processed_marks.csv",
        mime="text/csv",
    )
