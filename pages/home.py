"""
pages/home.py

Home / landing page for Student Performance Analytics.
"""

from __future__ import annotations

import streamlit as st


def show() -> None:
    """Render the Home page."""

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        '<h1 class="hero-title">Student Performance Analytics</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-subtitle">'
        "Upload your academic marks and turn them into meaningful insights."
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Two-column layout: What + How ─────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.markdown('<p class="section-heading">What is this?</p>', unsafe_allow_html=True)
        st.markdown(
            """
            A simple academic performance analytics dashboard that allows students to upload
            their marks data and visualize their performance across subjects and semesters.

            No registration. No login. Just upload your file and explore your results.
            """
        )

        st.markdown('<p class="section-heading">How it works</p>', unsafe_allow_html=True)
        steps = [
            ("1", "Prepare your marks data as a CSV or Excel file."),
            ("2", "Upload the file on the **Upload Data** page."),
            ("3", "Your data is validated and processed automatically."),
            ("4", "Explore interactive charts and insights on the **Visualization** page."),
        ]
        for num, text in steps:
            st.markdown(f"**{num}.** {text}")

    with col_right:
        st.markdown('<p class="section-heading">Features</p>', unsafe_allow_html=True)
        features = [
            "Easy CSV and Excel file upload",
            "Automatic data validation with clear error messages",
            "Subject-wise performance visualization",
            "Semester-wise performance tracking",
            "Overall percentage and key statistics",
            "Basic rule-based performance insights",
            "Download processed data as CSV",
        ]
        for f in features:
            st.markdown(f"✓ &nbsp; {f}", unsafe_allow_html=True)

        st.markdown('<p class="section-heading" style="margin-top:1.5rem;">Technology</p>', unsafe_allow_html=True)
        techs = ["Python", "Streamlit", "Pandas", "NumPy", "Plotly"]
        pills_html = "".join(f'<span class="tech-pill">{t}</span>' for t in techs)
        st.markdown(pills_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── CTA button ────────────────────────────────────────────────────────────
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("📤 Upload Your Data", width="stretch", type="primary"):
            st.session_state["page"] = "Upload"
            st.rerun()
