import streamlit as st


st.title("Part 2 - Data pipeline")
st.write(
	"This part extends the project by connecting API data with local and remote "
	"databases, data processing, and interactive Streamlit visualizations."
)

st.subheader("About the data")
st.write(
	"The NVE Magasinstatistikk API provides reservoir observations for Norway. "
	"The ENTSO-E Transparency Platform API provides physical electricity flows "
	"between Norway and neighbouring bidding zones."
)

st.subheader("Data pipeline")
st.write(
	"Raw observations are stored in Cassandra. Spark processes the electricity "
	"flows into monthly energy totals. The processed records are stored in MongoDB "
	"Atlas so that the deployed Streamlit application can access them."
)

st.subheader("What you can explore")
st.markdown(
	"""
	**NVE API:** Select an area type, area number, and date range to explore reservoir filling levels.

	**ENTSO-E API:** Select a partner connection and Norwegian bidding zone to inspect physical flows into and out of Norway.

	**MongoDB:** Select a connection and year to compare annual transfers and use the month pills to explore monthly values.
	"""
)

st.info("Use the navigation menu on the left to choose a Part 2 page.")
