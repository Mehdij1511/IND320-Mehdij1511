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
    .stApp { background: #DBF8F4; }
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

#Define the subtasks and their corresponding pages for each part of the project
subtasks_by_part = {
    "Part 1": {
        "Home": "ProjectPart1/Pages/Home.py",
        "Data table": "ProjectPart1/Pages/Data_table.py",
        "Interactive plotting": "ProjectPart1/Pages/Interactive_plotting.py",
        "Page four": "ProjectPart1/Pages/Page_four.py",
    },
    "Part 2": {
        "Home": "ProjectPart2/Pages/Home.py",
        "2.1": "ProjectPart2/Pages/2_1.py",
        "2.2": "ProjectPart2/Pages/2_2.py",
        "2.3": "ProjectPart2/Pages/2_3.py",
    },
    "Part 3": {
        "Home": "ProjectPart3/Pages/Home.py",
        "3.1": "ProjectPart3/Pages/3_1.py",
        "3.2": "ProjectPart3/Pages/3_2.py",
        "3.3": "ProjectPart3/Pages/3_3.py",
    },
    "Part 4": {
        "Home": "ProjectPart4/Pages/Home.py",
        "4.1": "ProjectPart4/Pages/4_1.py",
        "4.2": "ProjectPart4/Pages/4_2.py",
        "4.3": "ProjectPart4/Pages/4_3.py",
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
