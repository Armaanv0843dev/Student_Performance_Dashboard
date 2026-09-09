"""
app.py — Main entry point for Student Performance Analytics.

Single-file router: controls navigation via st.session_state["page"].
This approach ensures the sidebar shows only clean user-friendly labels
(not raw Python filenames like 'upload' or 'visualization').
"""

import streamlit as st

# ── Page configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Student Performance Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hide default Streamlit sidebar page links */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Sidebar branding */
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        padding: 0.5rem 0 1rem 0;
        letter-spacing: -0.3px;
    }

    .sidebar-divider {
        border: none;
        border-top: 1px solid #48A9F8FF;
        margin: 0.5rem 0 1rem 0;
    }

    /* Home page hero */
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        color: #48A9F8FF;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 1.15rem;
        color: #48A9F8FF;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Section headings */
    .section-heading {
        font-size: 0.8rem;
        font-weight: 600;
        color: #48A9F8;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Info card */
    .info-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }

    .info-card p {
        margin: 0;
        color: #334155;
        line-height: 1.7;
    }

    /* Feature grid */
    .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        margin-bottom: 0.5rem;
        color: #334155;
    }

    /* Tech pills */
    .tech-pill {
        display: inline-block;
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0.2rem;
    }

    /* KPI cards on visualization page */
    [data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
    }

    /* Page title */
    .page-title {
        font-size: 1.9rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.3rem;
    }

    .page-subtitle {
        font-size: 1rem;
        color: #48A9F8;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state initialisation ───────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">📊 Student Analytics</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<hr class="sidebar-divider">',
        unsafe_allow_html=True,
    )

    nav_options = [
        "🏠 Home",
        "📤 Upload Data",
        "✏️ Create Student Data",
        "📊 Visualization",
    ]

    label_to_page = {
        "🏠 Home": "Home",
        "📤 Upload Data": "Upload",
        "✏️ Create Student Data": "CreateData",
        "📊 Visualization": "Visualization",
    }

    page_to_label = {
        "Home": "🏠 Home",
        "Upload": "📤 Upload Data",
        "CreateData": "✏️ Create Student Data",
        "Visualization": "📊 Visualization",
    }

    current_label = page_to_label.get(st.session_state["page"], "🏠 Home")

    selected = st.radio(
        "Navigation",
        options=nav_options,
        index=nav_options.index(current_label),
        label_visibility="collapsed",
    )

    # Only change page if user actually selects something different
    selected_page = label_to_page[selected]

    if selected_page != st.session_state["page"]:
        st.session_state["page"] = selected_page
        st.rerun()

    st.markdown(
        '<hr class="sidebar-divider">',
        unsafe_allow_html=True,
    )

    st.caption(
        "Upload your marks data and explore your academic performance."
    )

    
# ── Page routing ───────────────────────────────────────────────────────────────
page = st.session_state["page"]

if page == "Home":
    from pages import home
    home.show()
elif page == "Upload":
    from pages import upload
    upload.show()
elif page == "CreateData":
    from pages import create_data
    create_data.show()
elif page == "Visualization":
    from pages import visualization
    visualization.show()
