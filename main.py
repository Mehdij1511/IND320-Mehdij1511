#import libraries
from pathlib import Path
import runpy
import streamlit as st

#determine root path of the project
PROJECT_ROOT = Path(__file__).parent

#Configure the Streamlit app
st.set_page_config(
    page_title="IND320 Portfolio APP",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

#Apply custom CSS styles to the app
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
    </style>
    """,
    unsafe_allow_html=True,
)

#Add a logo and title to the app
logo, title = st.columns([1, 2])
logo.image(PROJECT_ROOT / "NMBU_Logo.png", width=300)
title.title("IND320 Portfolio APP")
st.divider()

# Define the subtasks and their corresponding pages for each part of the project.
subtasks_by_part = {
    "Part 1": {
        "Home": "Pages/Part1/1Home.py",
        "Data table": "Pages/Part1/2Data_table.py",
        "Interactive plotting": "Pages/Part1/3Interactive_plotting.py",
        "Reservoir snapshot": "Pages/Part1/4Page_four.py",
    },
    "Part 2": {
        "Home": "Pages/Part2/1Home.py",
        "NVE API": "Pages/Part2/2NVE_API.py",
        "ENTSO-E API": "Pages/Part2/3ENTSOE_API.py",
        "MongoDB": "Pages/Part2/4MongoDB.py",
    },
}

#Add a sidebar for navigation between parts and pages
st.sidebar.title("Navigation")
st.sidebar.write("Select a task to navigate to its content.")
selected_part = st.sidebar.selectbox("Select a part", list(subtasks_by_part))
selected_page = st.sidebar.selectbox(
    f"Select a page for {selected_part}",
    list(subtasks_by_part[selected_part]),
)
st.sidebar.write(f"You selected: {selected_part} - {selected_page}")
st.sidebar.divider()

#Run the selected page if it exists, otherwise display an info message
page_path = PROJECT_ROOT / subtasks_by_part[selected_part][selected_page]
if page_path.exists():
    runpy.run_path(str(page_path), run_name="__main__")
else:
    st.info(f"Create the page file here: {page_path.relative_to(PROJECT_ROOT)}")
