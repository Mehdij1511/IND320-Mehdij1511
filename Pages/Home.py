import streamlit as st

# Introduce the purpose of Part 1 and the available pages.
st.title("Part 1 - Dashboard basics")
st.write(
    "This dashboard explores Norwegian reservoir data using tables and interactive visualizations."
)

# Give the user some background information about the dataset.
st.subheader("About the dataset")
st.write(
    "The data is stored in reservoirs.csv and contains weekly observations of reservoir areas, "
    "filling levels, capacity, filled volume, and changes from the previous week."
)

# Summarise the main features available through the navigation menu.
st.subheader("What you can explore")
st.markdown(
    """
    - **Data table:** Filter the data by reservoir area and year. Click a column header to sort the table.
    - **Interactive plotting:** Select an area, year, and measurement to explore changes over time.
    - **Reservoir snapshot:** Compare the latest filling levels between reservoir areas.
    """
)

# Direct the user to the sidebar to select another page.
st.info("Use the navigation menu on the left to choose a page.")
