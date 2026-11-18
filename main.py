# Import libraries
from pathlib import Path
import runpy

import streamlit as st

# Determine root path of the project
PROJECT_ROOT = Path(__file__).parent

# Configure the Streamlit app
st.set_page_config(
    page_title="IND320 Portfolio APP",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# Apply custom CSS styles to the app
st.markdown(
    """
    <style>
    .main-text { color: #000000; font-size: 1.5rem; }
    .stApp { background: #DBF8F4; color: #000000; }
    .block-container { padding: 3rem 2rem; }
    .stApp h1 { color: #025C4F; font-size: 3rem; }
    [data-testid="stSidebar"] { background: #008571; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label { color: #DBF8F4; }
    [data-testid="stSidebar"] .stButton > button {
        background: transparent;
        border: none;
        box-shadow: none;
        color: #DBF8F4;
        justify-content: flex-start;
        padding: 0.15rem 0 0.15rem 1.25rem;
        min-height: 0;
        text-align: left;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stButton > button:focus,
    [data-testid="stSidebar"] .stButton > button:active {
        background: transparent;
        border: none;
        box-shadow: none;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Add a logo and title to the app
logo, title = st.columns([1, 2])
logo.image(PROJECT_ROOT / "NMBU_Logo.png", width=300)
title.title("IND320 Portfolio APP")
st.divider()

# Organize the application by analysis topic.
pages = {
    "Overview": {
        "Overview": "app_pages/overview.py",
    },
    "Reservoirs": {
        "Reservoir snapshot": "app_pages/reservoir_snapshot.py",
        "Reservoir table": "app_pages/reservoir_table.py",
        "Reservoir plot": "app_pages/reservoir_plot.py",
        "Seasonality": "app_pages/reservoir_seasonality.py",
    },
    "Weather": {
        "Weather outliers": "app_pages/weather_outliers.py",
    },
    "Electricity flows": {
        "Live physical flows": "app_pages/entsoe_api.py",
        "Monthly processed flows": "app_pages/mongodb.py",
    },
    "Data sources": {
        "Sources and data lineage": "app_pages/data_sources.py",
    },
}

# Add a simple hierarchical sidebar navigation.
st.sidebar.title("Navigation")

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Overview"

for source, source_pages in pages.items():
    if source == "Overview":
        page_name = "Overview"
        if st.sidebar.button(
            page_name,
            key="nav_overview",
            use_container_width=True,
        ):
            st.session_state["selected_page"] = page_name
            st.rerun()
        continue

    st.sidebar.markdown(f"**{source}**")
    for page_name in source_pages:
        if st.sidebar.button(
            page_name,
            key=f"nav_{source}_{page_name}",
            use_container_width=True,
        ):
            st.session_state["selected_page"] = page_name
            st.rerun()

selected_page = st.session_state["selected_page"]

selected_source = next(
    source
    for source, source_pages in pages.items()
    if selected_page in source_pages
)

# Run the selected page if it exists, otherwise display an info message.
page_path = PROJECT_ROOT / pages[selected_source][selected_page]
if page_path.exists():
    runpy.run_path(str(page_path), run_name="__main__")
else:
    st.info(f"Create the page file here: {page_path.relative_to(PROJECT_ROOT)}")
