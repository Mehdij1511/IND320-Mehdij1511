import streamlit as st

st.title("Part 1 - Dashboard basics")
st.write(
	"This dashboard explores Norwegian reservoir data using tables and interactive visualizations."
)

st.subheader("About the dataset")
st.write(
	"The data is stored in reservoirs.csv and contains weekly observations of reservoir areas, "
	"filling levels, capacity, filled volume, and changes from the previous week."
)

st.subheader("What you can explore")
st.markdown(
	"""
	- **Data table:** Filter the data by reservoir area and year. Click a column header to sort the table.
	- **Interactive plotting:** Select an area, year, and measurement to explore changes over time.
	- **Page four:** Additional analysis and visualizations can be added here.
	"""
)

st.info("Use the navigation menu on the left to choose a page.")
