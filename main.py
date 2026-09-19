import streamlit as st

# Page Config
st.set_page_config(
    page_title="IND320 Portfolio APP",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)

# Custom CSS for styling, coloring in regards to NMBU design guidelines, and some padding for the main content area.
st.markdown("""
<style>
.stApp { background: #DBF8F4; }
.block-container { padding: 3rem 2rem; }
.stApp h1 { color: #025C4F; font-size: 2.4rem; margin: 1rem 0 2rem;}
[data-testid="stSidebar"] { background: #008571;}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {color: #DBF8F4;}
</style>
""", unsafe_allow_html=True)


# Header with logo and title (1 part for the logo, 2 parts for the title)
logo, title = st.columns([1, 2])
logo.image("Logo.jpg", width=100)
title.title("IND320 Portfolio APP")
st.divider()

#Sidebar with navigation:
st.sidebar.title("Navigation")
st.sidebar.write("Select a task to navigate to its content.")

#Main navigation
selected_task = st.sidebar.selectbox(
    label="Select a task",
    options=[
        "Part 1",
        "Part 2",
        "Part 3",
        "Part 4"
    ],
    index=0
)
st.sidebar.write(f"You selected: {selected_task}")
st.sidebar.divider()

# Secondary navigation based on the selected task.
subtasks_by_part = {
    "Part 1": ["1. Home", "1.2", "1.3"],
    "Part 2": ["2.1", "2.2", "2.3"],
    "Part 3": ["3.1", "3.2", "3.3"],
    "Part 4": ["4.1", "4.2", "4.3"],
}

selected_subtask = st.sidebar.selectbox(
    label=f"Select a subtask for {selected_task}",
    options=subtasks_by_part[selected_task],
    index=0,
)
st.sidebar.write(f"You selected: {selected_subtask}")
st.sidebar.divider()

# Page routing: convert the selected label to the existing renderer name.
renderer_name_by_subtask = {
    "1. Home": "render_home_page",
    # Copilot made this idea with the ** unpacking operator to generate the rest of the mapping dynamically.
    **{
        f"{part}.{number}": f"render_subtask_{part}_{number}"
        for part in range(1, 5)
        for number in range(1, 4)
        if not (part == 1 and number == 1)
    },
}
renderer = globals().get(renderer_name_by_subtask[selected_subtask])
if renderer:
    renderer()